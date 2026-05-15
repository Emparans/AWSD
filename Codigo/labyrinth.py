from collections import deque
import numpy as np
import cv2

dirs = ['u', 'r', 'd', 'l']

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

    def setTile():
        print("WIP")
            

class POI():
    def __init__(self):
        self.tile = None
        self.dirToLook = -1 # U = 0, R = 1, D = 2, L = 3
        self.h = -1
        self.time = 0

    def calculateHeuristic(self, currentNode):
        dist = np.sqrt((self.tile.x - currentNode.x)**2 + (self.tile.y - currentNode)**2)
        timeScaleFactor = np.sqrt(2) / 8
        self.h = np.max( dist - (timeScaleFactor * self.time), 0)
        self.time += 1


class Labyrinth():
    def __init__(self, nOfQuests):
        self.map = []
        self.poi = []
        
        self.remainingQuests = nOfQuests
        self.mapRemain = 36 #I assume that the map's always gonna be a 6x6

        self.score = 0

        self.currentX = self.currentY = 0
        self.currentDir = 0
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
                    if(n == dest):
                        found = True
                        break
                    else:
                        bfs.append(n)
                
        if(found):
            n = dest
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
                    if ppcomands.empty():
                        ppcomands.append(['f', 1])
                    else:
                        ppcomands[-1][1] += 1

            return ppcomands # We will send this to the robot. The output looks like: [['r', 2], ['r', 1], ['l', 3]]

        else:
            print(f"Camí de {self.currentNode} cap a {dest} no trobat.")
            self.selectNextPOI()        
            
    def selectNextPOI(self):
        if(self.poi.empty()):
            return None
        
        for p in self.poi:
            p.calculateHeuristic()
            
        self.poi.sort(key=lambda x: x.count, reverse=True)

        self.goToPoi()

    def updateFromImage():
        imgs=["Perspective", "Test1"]
        input_path = f"imagenesCénitales/{imgs[1]}.png"
        
        cv2.imread(input_path)

        


def start():
    lab = Labyrinth()
    lab.currentNode = Node()

    lab.currentNode.connect(0, 0)
    #SendSeq:
        #ScanForward
        #Turn
        #ScanForward
        #Turn
        #ScanForward
        #Turn
        #ScanForward





    