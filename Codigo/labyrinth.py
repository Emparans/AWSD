from collections import deque
import numpy as np
import cv2
from pathlib import Path

dirs = ['u', 'r', 'd', 'l']

interpretationSpots = np.array([
    #MIDDLE
    [400, 2700],
    [400, 2100],
    [400, 1500],
    [400,  900],
    [400,  300],

    #LEFT
    [75, 2500],
    [75, 1890],
    [75, 1280],
    [75,  670],
    [75,   60],

    #RIGHT
    [725, 2500],
    [725, 1890],
    [725, 1280],
    [725,  670],
    [725,   60]
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
        self.x = -1
        self.y = -1

    def connect(self, x, y):
        self.x = x
        self.y = y
        self.explored = True

    def setTile(self):
        print("WIP")
            

class POI():
    def __init__(self):
        self.tile = None
        self.dirToLook = -1 # U = 0, R = 1, D = 2, L = 3
        self.h = -1
        self.time = 0

    def calculateHeuristic(self, currentNode):
        dist = np.sqrt((self.tile.x - currentNode.x)**2 + (self.tile.y - currentNode.y)**2)
        timeScaleFactor = np.sqrt(2) / 8
        self.h = np.max( dist - (timeScaleFactor * self.time), 0)
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

    def goToPoi(self):
        dest = self.poi.pop(0)

        for m in self.map:
            m.prev = None
        
        self.currentNode.prev = self.currentNode

        bfs = deque()
        bfs.append(self.currentNode)

        found = False
        while bfs and not found:
            c = bfs.popleft()

            for dir in dirs:
                n = getattr(c, dir)

                if ((n != None) and (n.explored == True) and (n.prev == None)):
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

            commands = [] # f- forward, l- turn left + forward, r- turn right + forward, b- double turn right + forward
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
                
                n = path[-1]
                path.pop()

            ppcomands = []
            for cmd in commands:
                if cmd in ['l', 'r', 'b']:
                    ppcomands.append([cmd, 1])
                    
                elif cmd == 'f':
                    if len(ppcomands) == 0:
                        ppcomands.append(['f', 1])
                    else:
                        ppcomands[-1][1] += 1

            return ppcomands # We will send this to the robot. The output looks like: [['r', 2], ['r', 1], ['l', 3]]

        else:
            print(f"Camí de {self.currentNode} cap a {dest.tile} no trobat.")
            self.selectNextPOI()        
            
    def selectNextPOI(self):
        if(len(self.poi) == 0):
            return None
        
        for p in self.poi:
            p.calculateHeuristic(self.currentNode)
            
        self.poi.sort(key=lambda x: x.h, reverse=True)

        self.goToPoi()

    def updateFromImage(self):
        imgs=["Perspective", "Test1"]
        imgName = imgs[1]
        input_path = f"{Path(__file__).parent}/imagenesCenitales/{imgName}_cenitalBW.png"
        
        img = cv2.imread(input_path, 0)
        if img is None:
            print(f"No se pudo cargar la imagen en {input_path}")
            exit()

        # VIEW & SAVE DOTTED IMAGE
        # for i, pt in enumerate(interpretationSpots):
        #     cv2.circle(
        #         img,
        #         tuple(pt.astype(int)),
        #         7,
        #         (0, 0, 255),
        #         -1
        #     )

        # output_path = f"{Path(__file__).parent}/imagenesCenitales/{imgName}_cenitalBWDotted.png"
        # cv2.imwrite(output_path, img)
        # cv2.imshow("homo", img)
        
        # cv2.waitKey(0)

        t = 0
        for pt in interpretationSpots[0:5]:
            px, py = pt
            coords = self.currentPos
            dir = self.currentDir

            if(dir == 'u'):
                coords[1] += 1
            elif (dir == 'd'):
                coords[1] -= 1
            elif(dir == 'l'):
                coords[0] -= 1
            elif (dir == 'r'):
                coords[1] += 1

            tile = img[py, px] == 255

            if(tile):
                if(not self.map[coords]):
                    n = Node()
                    self.map[coords] = n
                    n.connect(coords[0], coords[1])
                
            else:
                break
            
            
lab = Labyrinth(3)
iN = Node()
lab.currentNode = iN
lab.map[(0, 0)] = iN
iN.connect(0, 0)

#SendSeq:
#ScanForward
#Turn
#ScanForward
#Turn
#ScanForward
#Turn
#ScanForward

lab.updateFromImage()





    