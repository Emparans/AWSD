from collections import deque
import numpy as np
import cv2
import json
from pathlib import Path

dirs = ['u', 'r', 'd', 'l']

interpretationSpots = np.array([
    #MIDDLE
    [400, 2699],
    [400, 2100],
    [400, 1500],
    [400,  900],
    [400,  300],

    #LEFT
    [70, 2630],
    [70, 2065],
    [70, 1450],
    [70,  815],
    [70,  180],

    #RIGHT
    [760, 2630],
    [760, 2065],
    [760, 1450],
    [760,  815],
    [760,  180]
], dtype=np.int32)

interpretationSpotsGT = np.array([
    #MIDDLE
    [118, 177],
    [238, 177],
    [358, 177],
    [478, 177],
    [598, 177],

    #LEFT
    [ 59, 123],
    [177, 123],
    [295, 123],
    [413, 123],
    [531, 123],

    #RIGHT
    [ 59, 243],
    [177, 243],
    [295, 243],
    [413, 243],
    [531, 243],
], dtype=np.int32)

class Node():
    def __init__(self):
        #Basic
        self.u = self.d = self.l = self.r  = None
        self.tile = -1 # Shape of walls to show on map
        self.explored = False
        self.mapped = False

        #Type related
        self.typeTile = 'X' # X = not discovered, O = Empty, K = Key, D = Door, ? = Question
        self.id = -1 # If it's a key or a door, it tracks the shape
        self.locked = False  # Just for doors, tracks its state
        self.dir = -1 # U = 0, R = 1, D = 2, L = 3, Relative to the map shown in web

        #Auxiliar
        self.prev = None
        self.coords = (-100, -100)

    def connect(self, x, y):
        self.coords = (x, y)
        self.explored = True

    def setTile(self, lab):
        x, y = self.coords
        if(self.u == None):
            if((x, y + 1) in lab.map):
                neighbor = lab.map[(x, y + 1)]
                self.u = neighbor
                neighbor.d = self
            else:
                lab.addPOI(self, 'u')
        if(self.d == None):
            if((x, y - 1) in lab.map):
                neighbor = lab.map[(x, y - 1)]
                self.d = neighbor
                neighbor.u = self
            else:
                lab.addPOI(self, 'd')
        if(self.l == None):
            if((x - 1, y) in lab.map):
                neighbor = lab.map[(x - 1, y)]
                self.l = neighbor
                neighbor.r = self
            else:
                lab.addPOI(self, 'l')
        if(self.r == None):
            if((x + 1, y) in lab.map):
                neighbor = lab.map[(x + 1, y)]
                self.r = neighbor
                neighbor.l = self
            else:
                lab.addPOI(self, 'r')

        self.tile = 0
        if self.u == 'Wall': self.tile += 1
        if self.r == 'Wall': self.tile += 2
        if self.d == 'Wall': self.tile += 4
        if self.l == 'Wall': self.tile += 8
            

class POI():
    def __init__(self, tile, dirToLook):
        self.tile = tile
        self.dirToLook = dirToLook #U, D, L, R
        self.h = -1
        self.time = 0

    def calculateHeuristic(self, currentNode):
        tx, ty = self.tile.coords
        cx, cy = currentNode.coords
        dist = abs(tx - cx) + abs(ty - cy)
        timeScaleFactor = np.sqrt(2) / 8
        self.h = max( dist - (timeScaleFactor * self.time), 0)
        self.time += 1


class Labyrinth():
    def __init__(self, nOfQuests):
        self.map = {}
        self.poi = []
        
        self.remainingQuests = nOfQuests
        self.mapRemain = 36 #I assume that the map's always gonna be a 6x6

        self.score = 0

        self.currentPos = (0, 0)
        self.currentDir = 'r'
        self.currentNode = None
        self.held = -1 # Id of the key the robot is carrying, -1 if none

    def addPOI(self, tile, dirToLook):
        if not any(p.tile == tile and p.dirToLook == dirToLook for p in self.poi):
            self.poi.append(POI(tile, dirToLook))

    def goToPoi(self):
        if not self.poi:
            return []

        dest = self.poi.pop(0)

        if getattr(dest.tile, dest.dirToLook) is not None:
            return self.goToPoi()

        for m in self.map.values():
            m.prev = None
        
        self.currentNode.prev = self.currentNode

        bfs = deque()
        bfs.append(self.currentNode)

        found = False
        if self.currentNode == dest.tile:
            found = True

        while bfs and not found:
            c = bfs.popleft()

            for dir in dirs:
                n = getattr(c, dir)

                if (isinstance(n, Node) and (n.explored == True) and (n.prev == None)):
                    n.prev = c
                    if(n == dest.tile):
                        found = True
                        break
                    else:
                        bfs.append(n)
                
        if(found):
            n = dest.tile
            path = deque()
            while n != self.currentNode:
                path.append(n)
                n = n.prev
            
            #n = currentnode here

            commands = [] # f- n forwards, l- turn left + n forwards, r- turn right + n forwards, b- double turn right + n forwards
            lastcommand = self.currentDir

            while path:
                if n.u == path[-1]:
                    if lastcommand == 'u':
                        commands.append("f")
                    elif lastcommand == 'r':
                        commands.append("l")
                    elif lastcommand == 'd':
                        commands.append("b")
                    elif lastcommand == 'l':
                        commands.append("r")
                    lastcommand = 'u'

                elif n.r == path[-1]:
                    if lastcommand == 'u':
                        commands.append("r")
                    elif lastcommand == 'r':
                        commands.append("f")
                    elif lastcommand == 'd':
                        commands.append("l")
                    elif lastcommand == 'l':
                        commands.append("b")
                    lastcommand = 'r'

                elif n.d == path[-1]:
                    if lastcommand == 'u':
                        commands.append("b")
                    elif lastcommand == 'r':
                        commands.append("r")
                    elif lastcommand == 'd':
                        commands.append("f")
                    elif lastcommand == 'l':
                        commands.append("l")
                    lastcommand = 'd'

                elif n.l == path[-1]:
                    if lastcommand == 'u':
                        commands.append("l")
                    elif lastcommand == 'r':
                        commands.append("b")
                    elif lastcommand == 'd':
                        commands.append("r")
                    elif lastcommand == 'l':
                        commands.append("f")
                    lastcommand = 'l'
                
                n = path.pop()                

            ppcomands = []
            for cmd in commands:
                if cmd in ['l', 'r', 'b']:
                    ppcomands.append([cmd, 1])
                    
                elif cmd == 'f':
                    if len(ppcomands) == 0:
                        ppcomands.append(['f', 1])
                    else:
                        ppcomands[-1][1] += 1

            if lastcommand != dest.dirToLook:
                turn_map = {
                    ('u', 'l'): 'l', ('u', 'r'): 'r', ('u', 'd'): 'b',
                    ('d', 'r'): 'l', ('d', 'l'): 'r', ('d', 'u'): 'b',
                    ('l', 'd'): 'l', ('l', 'u'): 'r', ('l', 'r'): 'b',
                    ('r', 'u'): 'l', ('r', 'd'): 'r', ('r', 'l'): 'b'
                }
                needed_turn = turn_map.get((lastcommand, dest.dirToLook))
                if needed_turn:
                    ppcomands.append([needed_turn, 0])

            #Will be updated elsewhere, in real time as the robot moves forward. This is only for debug purposes
            self.currentNode = dest.tile
            self.currentPos = dest.tile.coords
            self.currentDir = dest.dirToLook

            return ppcomands # We will send this to the robot. The output looks like: [['r', 2], ['r', 1], ['l', 3]]

        else:
            print(f"Camí de {self.currentNode} cap a {dest.tile} no trobat.")
            return self.selectNextPOI()        
            
    def selectNextPOI(self):
        if(len(self.poi) == 0):
            return None
        
        for p in self.poi:
            p.calculateHeuristic(self.currentNode)
            
        self.poi.sort(key=lambda x: x.h, reverse=False)
        return self.goToPoi()

    def updateFromImage(self, imgName):
        input_path = f"{Path(__file__).parent}/imagenesCenitales/{imgName}_cenitalBW.jpg"

        img = cv2.imread(input_path, 0)
        if img is None:
            print(f"No se pudo cargar la imagen en {input_path}")
            exit()

        # VIEW & SAVE DOTTED IMAGE
        # for i, pt in enumerate(interpretationSpots):
        #     cv2.circle(
        #         img,
        #         tuple(pt.astype(int)),
        #         k,
        #         (0, 0, 255),
        #         -1
        #     )

        # output_path = f"{Path(__file__).parent}/imagenesCenitales/{imgName}_cenitalBWDotted.png"
        # cv2.imwrite(output_path, img)
        # cv2.imshow("homo", img)
        
        # cv2.waitKey(0)

        #Process path
        k = 3 #Pixels to check around the interpretationSpots (2 = 5x5 area, 3 = 7x7 area...)
        th = 0.3
        tileKMultiplier = 5

        prev = self.currentNode
        coords = list(self.currentPos)
        dir = self.currentDir
        tilesToUpdate = deque()
        for pt in interpretationSpots[0:5]:
            if(dir == 'u'):
                coords[1] += 1
            elif (dir == 'd'):
                coords[1] -= 1
            elif(dir == 'l'):
                coords[0] -= 1
            elif (dir == 'r'):
                coords[0] += 1

            current_coords = tuple(coords)

            px, py = pt
            y1 = max(0, py - (k * tileKMultiplier))
            y2 = min(img.shape[0], py + (k * tileKMultiplier) + 1)
            x1 = max(0, px - (k * tileKMultiplier))
            x2 = min(img.shape[1], px + (k * tileKMultiplier) + 1)

            roi = img[y1:y2, x1:x2]

            tile = np.mean(roi < 128) > 0.7

            if(tile):
                if(current_coords not in self.map):
                    n = Node()
                    self.map[current_coords] = n
                    n.connect(current_coords[0], current_coords[1])
                    self.mapRemain -= 1
                else:
                    n = self.map[current_coords]
                
                setattr(prev, dir, n)
                if(dir == 'u'):
                    setattr(n, 'd', prev)
                elif (dir == 'd'):
                    setattr(n, 'u', prev)
                elif(dir == 'l'):
                    setattr(n, 'r', prev)
                elif (dir == 'r'):
                    setattr(n, 'l', prev)
                
                prev = n
                tilesToUpdate.append(n)
            else:
                break

        if dir == 'u' and prev.u is None: prev.u = 'Wall'
        elif dir == 'd' and prev.d is None: prev.d = 'Wall'
        elif dir == 'l' and prev.l is None: prev.l = 'Wall'
        elif dir == 'r' and prev.r is None: prev.r = 'Wall'

        #Add Walls
        for i, t in enumerate(tilesToUpdate):
            #Left
            px, py = interpretationSpots[i + 5]

            y1 = max(0, py - k)
            y2 = min(img.shape[0], py + k + 1)
            x1 = max(0, px - k)
            x2 = min(img.shape[1], px + k + 1)

            roi = img[y1:y2, x1:x2]

            is_wall = np.mean(roi > 128) > th

            if(is_wall):
                if(dir == 'u' and t.l is None):
                    t.l = 'Wall'
                elif (dir == 'd' and t.r is None):
                    t.r = 'Wall'
                elif(dir == 'l' and t.d is None):
                    t.d = 'Wall'
                elif (dir == 'r' and t.u is None):
                    t.u = 'Wall'

            #Right
            px, py = interpretationSpots[i + 10]
            y1 = max(0, py - k)
            y2 = min(img.shape[0], py + k + 1)
            x1 = max(0, px - k)
            x2 = min(img.shape[1], px + k + 1)

            roi = img[y1:y2, x1:x2]

            is_wall = np.mean(roi > 128) > th

            if(is_wall):
                if(dir == 'u' and t.r is None):
                    t.r = 'Wall'
                elif (dir == 'd' and t.l is None):
                    t.l = 'Wall'
                elif(dir == 'l' and t.u is None):
                    t.u = 'Wall'
                elif (dir == 'r' and t.d is None):
                    t.d = 'Wall'

        #Process inverse path to set tiles
        while len(tilesToUpdate) > 0:
            t = tilesToUpdate.pop()
            t.setTile(self)

        return self.selectNextPOI()

    def generateGT(self, imgName):
        input_path = f"{Path(__file__).parent}/gt/{imgName}.jpg"
        
        img = cv2.imread(input_path, 0)
        if img is None:
            print(f"No se pudo cargar la imagen en {input_path}")
            exit()

        kernel = np.ones((7,7), np.uint8)
        img = cv2.morphologyEx(img, cv2.MORPH_DILATE, kernel)

        # VIEW & SAVE DOTTED IMAGE
        # for i, pt in enumerate(interpretationSpotsGT):
        #     cv2.circle(
        #         img,
        #         tuple(pt.astype(int)),
        #         7,
        #         (0, 0, 255),
        #         -1
        #     )

        # output_path = f"{Path(__file__).parent}/gt/{imgName}_Dotted.png"
        # cv2.imwrite(output_path, img)
        # cv2.imshow("gt", img)
        
        # cv2.waitKey(0)

        dir = self.currentDir 
        coords = list(self.currentPos)
        prev = self.currentNode
        
        tilesToUpdate = deque()

        for i in range(5):
            if dir == 'r': coords[0] += 1
            elif dir == 'l': coords[0] -= 1
            elif dir == 'u': coords[1] += 1
            elif dir == 'd': coords[1] -= 1
            
            current_coords = tuple(coords)
            
            if current_coords not in self.map:
                n = Node()
                self.map[current_coords] = n
                n.connect(current_coords[0], current_coords[1])
                self.mapRemain -= 1
            else:
                n = self.map[current_coords]

            setattr(prev, dir, n)
            if dir == 'r': n.l = prev
            elif dir == 'l': n.r = prev
            elif dir == 'u': n.d = prev
            elif dir == 'd': n.u = prev
            
            px_l, py_l = interpretationSpotsGT[i + 5]
            px_r, py_r = interpretationSpotsGT[i + 10]
            
            if img[py_l, px_l] > 128:
                if dir == 'r': n.u = 'Wall'
                elif dir == 'l': n.d = 'Wall'
                elif dir == 'u': n.l = 'Wall'
                elif dir == 'd': n.r = 'Wall'

            if img[py_r, px_r] > 128:
                if dir == 'r': n.d = 'Wall'
                elif dir == 'l': n.u = 'Wall'
                elif dir == 'u': n.r = 'Wall'
                elif dir == 'd': n.l = 'Wall'

            tilesToUpdate.append(n)

            px_m, py_m = interpretationSpotsGT[i]
            
            if img[py_m, px_m] > 128:
                if dir == 'r': n.r = 'Wall'
                elif dir == 'l': n.l = 'Wall'
                elif dir == 'u': n.u = 'Wall'
                elif dir == 'd': n.d = 'Wall'
                break
                
            prev = n

        if dir == 'u' and prev.u is None: prev.u = 'Wall'
        elif dir == 'd' and prev.d is None: prev.d = 'Wall'
        elif dir == 'l' and prev.l is None: prev.l = 'Wall'
        elif dir == 'r' and prev.r is None: prev.r = 'Wall'

        while len(tilesToUpdate) > 0:
            t = tilesToUpdate.pop()
            t.setTile(self)
            
    def printLab(self):
        #FUNCIÓN GENERADA CON IA
        if not self.map:
            return "Empty Map"

        min_x = min(x for x, y in self.map.keys())
        max_x = max(x for x, y in self.map.keys())
        min_y = min(y for x, y in self.map.keys())
        max_y = max(y for x, y in self.map.keys())


        cols = (max_x - min_x + 1) * 4 + 1
        rows = (max_y - min_y + 1) * 2 + 1
        
        grid = [[' ' for _ in range(cols)] for _ in range(rows)]

        poi_coords = {p.tile.coords for p in self.poi if hasattr(p.tile, 'coords')}
        
        dir_chars = {'u': '^', 'd': 'v', 'l': '<', 'r': '>'}

        for (x, y), node in self.map.items():
            cx = (x - min_x) * 4 + 2
            cy = (max_y - y) * 2 + 1

            grid[cy-1][cx-2] = '+'
            grid[cy-1][cx+2] = '+'
            grid[cy+1][cx-2] = '+'
            grid[cy+1][cx+2] = '+'

            if (x, y) == self.currentPos:
                grid[cy][cx] = dir_chars.get(self.currentDir, 'R')
            elif (x, y) in poi_coords:
                grid[cy][cx] = '*'
            else:
                grid[cy][cx] = '.'

            u_char = '-' if node.u == 'Wall' else '?' if node.u is None else ' '
            grid[cy-1][cx-1] = u_char
            grid[cy-1][cx]   = u_char
            grid[cy-1][cx+1] = u_char

            d_char = '-' if node.d == 'Wall' else '?' if node.d is None else ' '
            grid[cy+1][cx-1] = d_char
            grid[cy+1][cx]   = d_char
            grid[cy+1][cx+1] = d_char

            l_char = '|' if node.l == 'Wall' else '?' if node.l is None else ' '
            grid[cy][cx-2] = l_char

            r_char = '|' if node.r == 'Wall' else '?' if node.r is None else ' '
            grid[cy][cx+2] = r_char

        return("\n".join("".join(row) for row in grid))

    def toJSON(self):
        #FUNCIÓN GENERADA CON IA
        nodes_list = []
        for coords, node in self.map.items():
            def parse_boundary(b):
                if b == 'Wall': return 'Wall'
                if b is None: return None
                return 'Node'

            nodes_list.append({
                "coords": list(coords),
                "explored": node.explored,
                "mapped": node.mapped,
                "typeTile": node.typeTile,
                "id": node.id,
                "locked": node.locked,
                "boundaries": {
                    "u": parse_boundary(node.u),
                    "d": parse_boundary(node.d),
                    "l": parse_boundary(node.l),
                    "r": parse_boundary(node.r)
                }
            })

        pois_list = []
        for p in self.poi:
            pois_list.append({
                "targetCoords": list(p.tile.coords),
                "dirToLook": p.dirToLook
            })

        payload = {
            "state": {
                "remainingQuests": self.remainingQuests,
                "mapRemain": self.mapRemain,
                "score": self.score
            },
            "robot": {
                "currentPos": list(self.currentPos),
                "currentDir": self.currentDir,
                "held": self.held
            },
            "nodes": nodes_list,
            "pois": pois_list
        }

        return json.dumps(payload, indent=2)            

def find_wall_errors(labGT, labHomo):
    errors = []
    
    for coords, gt_node in labGT.map.items():
        if coords not in labHomo.map:
            errors.append(f"  [!] Missing Tile: GT found a tile at {coords}, but Homo missed it.")
            continue

        homo_node = labHomo.map[coords]

        for d in ['u', 'd', 'l', 'r']:
            gt_is_wall = (getattr(gt_node, d) == 'Wall')
            homo_is_wall = (getattr(homo_node, d) == 'Wall')

            if gt_is_wall != homo_is_wall:
                errors.append(f"  [-] Mismatch at Tile {coords} | Dir '{d}': GT says Wall={gt_is_wall}, Homo says Wall={homo_is_wall}")
                
    return errors

def start():      
    lab = Labyrinth(3)
    iN = Node()
    lab.currentNode = iN
    lab.map[(0, 0)] = iN
    iN.connect(0, 0)
    lab.mapRemain -= 1

    iN.setTile(lab)
    return lab

correct = 0

for i in range(60):
    imgs = f"img_{i}"
    labHomo = start()
    labGT = start()

    labGT.generateGT(imgs)
    gt = labGT.printLab()

    labHomo.updateFromImage(imgs)
    labHomo.currentDir = 'r'
    homo = labHomo.printLab()

    if(gt == homo):
        correct += 1
    else:
        print(find_wall_errors(labGT, labHomo))
     

print(correct)
