#!/usr/bin/python

from collections import namedtuple
import time
import sys

class Edge:
    def __init__ (self, origin=None):
        self.origin = 0 # IATA code del origen
        self.weight = 1.0 # numero de vegades que hi ha aquesta ruta

    def __repr__(self):
        return "edge: {0} {1}".format(self.origin, self.weight)
        
    ## write rest of code that you need for this class

class Airport:
    def __init__ (self, iden=None, name=None):
        self.code = iden
        self.name = name
        self.routes = []
        self.routeHash = dict()
        self.outweight = 0.0  # numero de rutes totals cap a altres aeroports
        self.listIndex= 0

    def __repr__(self):
        return f"{self.code}\t Nom: {self.name}\t numRutesUniques: {len(self.routes)}"

edgeList = [] # list of Edge
edgeHash = dict() # hash of edge to ease the match
airportList = [] # list of Airport
airportHash = dict() # hash key IATA code -> Airport
noOutWeight = 0.0
pageRank = []
error= 10**(-16)


def readAirports(fd):
    print("Reading Airport file from {0}".format(fd))
    airportsTxt = open(fd, "r");
    cont = 0
    for line in airportsTxt.readlines():
        a = Airport()
        try:
            temp = line.split(',')
            if len(temp[4]) != 5 :
                raise Exception('not an IATA code')
            a.name=temp[1][1:-1] + ", " + temp[3][1:-1]
            a.code=temp[4][1:-1]
        except Exception as inst:
            pass
        else:
            a.listIndex=cont
            cont += 1
            airportList.append(a)
            airportHash[a.code] = a
    airportsTxt.close()
    print(f"There were {cont} Airports with IATA code")


def readRoutes(fd):
    print("Reading Routes file from {0}".format(fd))
    routesTxt = open(fd, "r");
    cont = 0
    for line in routesTxt.readlines():
        e = Edge()
        try:
            temp = line.split(',')

            codeOrigin = temp[2]
            codeDestination = temp[4]
            ## no se si es molt costos aixo per a cada ruta
            if codeOrigin not in airportHash:
                raise Exception('Origin airport has no IATA code')
            if codeDestination not in airportHash:
                raise Exception('Destination airport has no IATA code')
            
        except Exception as inst:
            pass

        else:
            airportHash[codeOrigin].outweight +=1
            a = airportHash[codeDestination]
            if codeOrigin in a.routeHash:
                a.routeHash[codeOrigin].weight +=1.0
            else :
                e.origin = codeOrigin
                e.weight = 1.0
                a.routeHash[codeOrigin] =e
                a.routes.append(e)
                cont+=1

    routesTxt.close()
    print(f"There were {cont} distinct routes between IATA airports")

def sumaVec(vec):
    suma = 0
    for v in vec:
        suma += v
    return suma

def computePageRanks():
    n = len(airportList)
    P = [1/n]*n     #vector de n elements que sumen 1
    L = 0.85      #dampening factor, normalment entre 0.8 i 0.9

    iteracions = 0
    condition = True
    #print(noOutWeight)

    # percompensar els nodes amb outweight 0, repartirm el seu pes equivalent entre tots els altres nodes
    # creant aixi uns "edges virtuals" que els conecten a tots els altres nodes
    pesNoOutWeight = 1/n
    numOut = L*noOutWeight/n #L*((noOutWeight*1.0/n)/n) 
    while (condition):
        Q = [0.0]*n
        
        for i in range(0,n):

            sum=0
            for edge in airportList[i].routes:
                indexJ = airportHash[edge.origin].listIndex
                sum += (P[indexJ]*edge.weight)/airportList[indexJ].outweight
            Q[i] = L * sum + (1.0-L)/n + pesNoOutWeight * numOut
        
        #print(sumaVec(Q))
        #per a cada iteracio, el pes de els nodes sense outweight sera la expressio de abaix, ja que la seva sum sempre sera 0
        pesNoOutWeight = (1-L)/n + pesNoOutWeight*numOut
        
        iteracions += 1
        
        k = [abs(x - y) for x,y in zip(P, Q)] 
        condition = all(map(lambda val: val > error,k))
        #condition = (iteracions < 15)

        P = Q

    global pageRank
    pageRank = P
    return iteracions



def outputPageRanks():
    indexos = [i for i in range(0,len( airportList ))]
    l = [(index,rank)for index,rank in zip(indexos,pageRank)]
    #print(l)
    l.sort(key = lambda x: x[1],reverse=True) 
    for x in range(0,len(l)):
        code= l[x][0]
        print("Rank {0} : ".format(x+1)), print(airportList[ code ])

def main(argv=None):
    readAirports("airports.txt")
    readRoutes("routes.txt")
    global noOutWeight
    noOutWeight = len(list(filter(lambda n: n.outweight == 0, airportList)))


    
    time1 = time.time()
    iterations = computePageRanks()
    time2 = time.time()
    outputPageRanks()
    print("#Iterations:", iterations)
    print("Time of computePageRanks():", time2-time1)


if __name__ == "__main__":
    sys.exit(main())
