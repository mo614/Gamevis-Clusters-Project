## CS:GO Example Clustering Script
##
## Requirements:
## SciPy
## NumPy
## Shapely

import numpy as np
import csv, os, math
import json
from scipy.spatial import ConvexHull

from sklearn.cluster import DBSCAN
from sklearn import metrics
from sklearn.preprocessing import StandardScaler

import shapely.geometry as geometry
from descartes import PolygonPatch
from shapely.ops import cascaded_union, polygonize
from scipy.spatial import Delaunay

def alpha_shape(points, alpha):
    
    if len(points) < 4:
        # If there is a triangle, no need to find an alpha shape.
        return geometry.MultiPoint(list(points)).convex_hull, list(points)
    def add_edge(edges, edge_points, coords, i, j):

        if (i, j) in edges or (j, i) in edges:
            # already added
            return
        edges.add( (i, j) )
        edge_points.append(coords[ [i, j] ])

        
    tri = Delaunay(points)
    edges = set()
    edge_points = []
    # loop over triangles:
    # ia, ib, ic = indices of corner points of the
    # triangle
    for ia, ib, ic in tri.vertices:
        #Get points of triangle
        pa = points[ia]
        pb = points[ib]
        pc = points[ic]
        
        # Lengths of sides of triangle
        a = math.sqrt((pa[0]-pb[0])**2 + (pa[1]-pb[1])**2)
        b = math.sqrt((pb[0]-pc[0])**2 + (pb[1]-pc[1])**2)
        c = math.sqrt((pc[0]-pa[0])**2 + (pc[1]-pa[1])**2)
        
        # Semiperimeter of triangle
        s = (a + b + c)/2.0
        
        # Area of triangle by Heron's formula
        area = math.sqrt(s*(s-a)*(s-b)*(s-c))

        #find Circumradius
        circum_r = a*b*c/(4.0*area)
        
        # Check if Circumradius is within criteria
        if circum_r < 1.0/alpha:
            add_edge(edges, edge_points, points, ia, ib)
            add_edge(edges, edge_points, points, ib, ic)
            add_edge(edges, edge_points, points, ic, ia)
    m = geometry.MultiLineString(edge_points)
    triangles = list(polygonize(m))
    return cascaded_union(triangles), edge_points

def getJsonObject(string):
    return json.loads(string)

def generateClusters(dictTimes):
    dictClusters = {}
    for key in dictTimes.keys():
        ##prepare data for clustering
        length = len(dictTimes)
        X = np.array(dictTimes[key])
        #X = np.ndarray(shape=(length,2), buffer=arrayToCluster)
        db = DBSCAN(eps=80, min_samples=30,).fit(X)
        core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
        core_samples_mask[db.core_sample_indices_] = True
        labels = db.labels_
        dictClusters[key] = labels

    return dictClusters



def findClusterWinRates(dictTimes, dictClusters, dictPointers):
    #for each cluster at a time, determine win probability
    dictClusterWinRate = {}
    for time in dictTimes.keys():
        uniqueLabels = np.unique(dictClusters[time])
        winRates = {}
        
        for cluster in uniqueLabels:
            
            
            countWin = 0
            countLoss = 0
            countDraw = 0
            countTotal = 0
        
            #go through all labels at this time,
            for n in range(0, len(dictClusters[time])):
                
                #if it is the cluster we are interested in:
                if (dictClusters[time][n] == cluster):
                    #find same position in pointers dict
                    #check if win/loss/draw
                    if (dictPointers[time][n]['win'] == 1):
                        countWin += 1
                    elif (dictPointers[time][n]['win'] == 0):
                        countDraw += 1
                    elif (dictPointers[time][n]['win'] == -1):
                        countLoss += 1
                    countTotal += 1

            #now find win %
            #add this to a dictionary for this time 
            if (countWin + countLoss + countDraw != countTotal):
                raise Exception("wins/losses/draws don't add up for time: " + str(time))

            percentWin = countWin / countTotal * 100

            winRates[str(cluster)] = percentWin

        dictClusterWinRate[time] = winRates
        
    print("Finished calculating win rates")
    return dictClusterWinRate

def generateConcaveHulls(dictTimes, dictClusters, dictPointers):
        
    ##now produce convex hull for each cluster at times
    dictClusterShapes = {}
    for time in dictTimes.keys():

        uniqueLabels = np.unique(dictClusters[time])
        convexHulls = {}

        for cluster in uniqueLabels:
            if (cluster != -1): #if not outliers which have no convex hull
                pointsToInclude = []
                
         
                #go through all labels 
                for n in range(0, len(dictClusters[time])):
                    
                    #if it is the cluster we are interested in:
                    if (dictPointers[time][n]['cluster'] == cluster):
                        #find same position in pointers dict
                        #add it to points we'll use to to find convex hull
                        pointsToInclude.append([dictPointers[time][n]['position']['x'], dictPointers[time][n]['position']['y']])
                
                #convert list to ndarray
                length = len(pointsToInclude)
                if (length > 2):
                    standardArray = np.array(pointsToInclude)
                    arrayToFindShape = np.ndarray(shape=(length,2), buffer=standardArray)
                    
                    #now find concave hull
                    #add this to a dictionary for this time 
                    alphaVal=0.01
                    concave_hull, edge_points = alpha_shape(arrayToFindShape, alpha=alphaVal)
                    while (type(concave_hull) is not geometry.polygon.Polygon):
                        print("concave_hull was actually " + str(type(concave_hull)))
                        alphaVal -= alphaVal * 0.05
                        print ("using alphaVal=" + str(alphaVal))
                        concave_hull, edge_points = alpha_shape(arrayToFindShape, alpha=alphaVal)

                    hullPoints = []
                    for point in concave_hull.exterior.coords:
                        hullPoints.append(point)

                    convexHulls[str(cluster)] = hullPoints

        dictClusterShapes[time] = convexHulls

    print("Finished finding cluster shapes")
    return dictClusterShapes


########################################################################################################
########################################################################################################
###### CS:GO CLUSTER GENERATION MAIN PROGRAM #####
########################################################################################################
########################################################################################################

globalRoundCount = 0
fileCount = 0

timePeriod = 2 #we want data for every 2 seconds
tickRate = 128 #number of ticks per second
listOfAllCoordinates = []
listOfTeams = {}
listOfWinningTeams = {}
output = []

listOfAlreadyListedPlayers = []
mostRecentPositions = {}
listOfDeaths = {}
nextTickToPoll = timePeriod * tickRate
mostRecentStart = -1
roundCount = 0

directory = "Data\\"

for filename in os.listdir(directory):
    if filename.endswith(".dat"):
        fileCount += 1
        print("Parsing file " + str(fileCount) + ": " + filename)
        
        with open(directory + filename, 'r', encoding="utf8") as f:
            
            reader = csv.reader(f, delimiter='\t')
            #currentGame = -1
            for row in reader:


                if ((mostRecentStart != -1) and (int(row[0]) - mostRecentStart > nextTickToPoll)):

                    #add most recent steps to output
                    output.append([nextTickToPoll, mostRecentPositions])

                    #reset mostRecentPositions
                    mostRecentPositions = {}

                    nextTickToPoll += timePeriod * tickRate


                if (row[1] == 'round_start'):

                    globalRoundCount += 1

                    #increment round count
                    roundCount += 1
                    
                    #reset most recent start         
                    mostRecentStart = int(row[0]) + (15 * tickRate) #account for 15 second freeze time

                    #reset next tick to poll
                    nextTickToPoll = timePeriod * tickRate
                    
                    if (roundCount not in listOfTeams.keys()):
                        #reset list of teams
                        listOfTeams[roundCount] = []
                    
                    #reset list of deaths
                    listOfDeaths[roundCount] = []

                elif (row[1] == 'player_spawn'):

                    if (mostRecentStart == -1):
                        #if we are between rounds the spawns will be for the next round that is yet to start
                        roundOfSpawn = roundCount + 1#raise Exception("Unexpected player spawn after round start")
                    else:
                        roundOfSpawn = roundCount
                    
                    if (roundOfSpawn not in listOfTeams.keys()):
                        #reset list of teams
                        listOfTeams[roundOfSpawn] = []

                    if(roundOfSpawn == 16):
                        pass

                        
                    #wrap this in try/except, since data sometimes has phantom spawns with incomplete data since this is before the round actually starts
                    try: 
                        #set most_recent_playerposition
                        playerNumber = getJsonObject(row[4])['player']
                        
                        ###commenting this out means a player has to move to be included in data##
                        ##but at least it means players who spawn but aren't actually on a team are excluded##
                        #mostRecentPositions[playerNumber] = [getJsonObject(row[3])['player'],roundCount] 

                        #set playerTeam for this round
                        team = getJsonObject(row[2])['teamnum']
                        listOfTeams[roundOfSpawn].append({'playerNumber': playerNumber, 'teamNumber': team})
                    except TypeError:
                        pass

                elif (mostRecentStart > -1):

                    if (row[1] == 'player_death'):

                        try:
                            
                            #set player death for round number
                            playerNumber = getJsonObject(row[4])['player']

                            #if (len(listOfDeaths) <= roundCount):
                            #    listOfDeaths.append([])

                            #print({'playerNumber': playerNumber, tick: int(row[0])})
                                
                            listOfDeaths[roundCount].append({'playerNumber': playerNumber, 'tick': int(row[0]), 'relativeTick': int(row[0]) - mostRecentStart})
                            
                        except Exception:
                                pass     
                       
                    elif (row[1] == 'round_end'):
                        

                        #make mostRecentStart invalid so we check we're not doing something stupid
                        mostRecentStart = -1

                        #add the winning team to the listOfWinners in position of roundCount
                        winner = getJsonObject(row[2])['winner']

                        if roundCount not in listOfWinningTeams:
                            listOfWinningTeams[roundCount] = (winner)
                        else:
                            raise Exception("Round can't end twice.")

                        #reset mostRecentPositions
                        mostRecentPositions = {}

                    elif (row[1] == 'begin_new_match' or row[1] == 'cs_pre_restart' or row[1] == 'round_prestart'): ##These handle round restarts where a round does not formally 'end'
                        
                        #make mostRecentStart invalid so we check we're not doing something stupid
                        mostRecentStart = -1

                        #reset mostRecentPositions
                        mostRecentPositions = {}
                    
                    elif (row[1] == 'player_footstep'):
                        try:
                            if (mostRecentStart == -1):
                                raise exception("cant have footstep before round start")
                            
                            playerNumber = getJsonObject(row[4])['player']

                            mostRecentPositions[playerNumber] = [getJsonObject(row[3])['player'],roundCount, filename]

                        except TypeError:
                            pass

print("Parsing files done")
print("Rounds parsed: " + str(globalRoundCount))

##Now we have all the data we want, we can produce data to be fed to clustering algorithm

winTdictTimes = {}
winTdictPointers = {}
winCTdictTimes = {}
winCTdictPointers = {}
lossTdictTimes = {}
lossTdictPointers = {}
lossCTdictTimes = {}
lossCTdictPointers = {}
for timeData in output:

    for key in timeData[1].keys():

        ##if we have a winner add this to data we'll track,
        ##otherwise ignore, its likely players messing around after rounds end but before server closes
        if (timeData[1][key][1] in listOfWinningTeams.keys()):
            
            

            #did this player die?
            for death in listOfDeaths[timeData[1][key][1]]:
                if (death['playerNumber'] == key):
                    thisDeath = [True, death['relativeTick'], death['tick']]
                    break
                else:
                    thisDeath = [False,-1,-1]

            #find team of this player
            for team in listOfTeams[timeData[1][key][1]]:
                if (team['playerNumber'] == key):
                    thisTeam = team['teamNumber']

            #find which team won
            winner = listOfWinningTeams[timeData[1][key][1]]
            if (winner == thisTeam):
                thisWin = 1
            elif (winner == 1):
                thisWin = 0 #0 winner indicates draw
            else:
                thisWin = -1

            if (thisTeam == 2): #terrorists:

                if (thisWin == 1):

                    if (timeData[0] not in winTdictTimes):
                        winTdictTimes[timeData[0]] = []
                        winTdictPointers[timeData[0]] = []

                    winTdictTimes[timeData[0]].append([timeData[1][key][0]['x'], timeData[1][key][0]['y']])
                        
                    winTdictPointers[timeData[0]].append({'round':timeData[1][key][1], 'filename':timeData[1][key][2], 'playerNumber': key, 'team':thisTeam, 'position': timeData[1][key][0],
                                                        'win': thisWin, 'death': thisDeath })

                elif (thisWin == -1):

                    if (timeData[0] not in lossTdictTimes):
                        lossTdictTimes[timeData[0]] = []
                        lossTdictPointers[timeData[0]] = []

                    lossTdictTimes[timeData[0]].append([timeData[1][key][0]['x'], timeData[1][key][0]['y']])
                        
                    lossTdictPointers[timeData[0]].append({'round':timeData[1][key][1], 'filename':timeData[1][key][2], 'playerNumber': key, 'team':thisTeam, 'position': timeData[1][key][0],
                                                        'win': thisWin, 'death': thisDeath })

            elif (thisTeam == 3): #counter terrorists

                if (thisWin == 1):
                    
                    if (timeData[0] not in winCTdictTimes):
                        winCTdictTimes[timeData[0]] = []
                        winCTdictPointers[timeData[0]] = []

                    winCTdictTimes[timeData[0]].append([timeData[1][key][0]['x'], timeData[1][key][0]['y']])
                        
                    winCTdictPointers[timeData[0]].append({'round':timeData[1][key][1], 'filename':timeData[1][key][2], 'playerNumber': key, 'team':thisTeam, 'position': timeData[1][key][0],
                                                        'win': thisWin, 'death': thisDeath })

                elif (thisWin == -1):
                    
                    if (timeData[0] not in lossCTdictTimes):
                        lossCTdictTimes[timeData[0]] = []
                        lossCTdictPointers[timeData[0]] = []

                    lossCTdictTimes[timeData[0]].append([timeData[1][key][0]['x'], timeData[1][key][0]['y']])
                        
                    lossCTdictPointers[timeData[0]].append({'round':timeData[1][key][1], 'filename':timeData[1][key][2], 'playerNumber': key, 'team':thisTeam, 'position': timeData[1][key][0],
                                                        'win': thisWin, 'death': thisDeath })

            else:
                if (thisTeam != 0): #if team is 0, ignore it is probably just a non-game state of setting up teams
                    raise Exception("unrecognised team")
                

print("TdictTime and CTdictTime done")

####WINNING TEAM TERRORISTS 

winTdictClusters = generateClusters(winTdictTimes)
winTdictClusterWinRate = findClusterWinRates(winTdictTimes, winTdictClusters, winTdictPointers)

for time in winTdictTimes.keys():
    for n in range(0, len(winTdictClusters[time])):
        winTdictPointers[time][n]['cluster'] = int(winTdictClusters[time][n]) #need to convert to int otherwise numpy.int64 which can't be JSON serialised are used

winTdictClusterShapes = generateConcaveHulls(winTdictTimes, winTdictClusters, winTdictPointers)

####WINNING TEAM TERRORISTS 

lossTdictClusters = generateClusters(lossTdictTimes)
lossTdictClusterWinRate = findClusterWinRates(lossTdictTimes, lossTdictClusters, lossTdictPointers)

for time in lossTdictTimes.keys():
    for n in range(0, len(lossTdictClusters[time])):
        lossTdictPointers[time][n]['cluster'] = int(lossTdictClusters[time][n]) #need to convert to int otherwise numpy.int64 which can't be JSON serialised are used

lossTdictClusterShapes = generateConcaveHulls(lossTdictTimes, lossTdictClusters, lossTdictPointers)


####REPEAT FOR COUNTER TERRORISTS WINNING TEAM:

winCTdictClusters = generateClusters(winCTdictTimes)
winCTdictClusterWinRate = findClusterWinRates(winCTdictTimes, winCTdictClusters, winCTdictPointers)

for time in winCTdictTimes.keys():
    for n in range(0, len(winCTdictClusters[time])):
        winCTdictPointers[time][n]['cluster'] = int(winCTdictClusters[time][n]) #need to convert to int otherwise numpy.int64 which can't be JSON serialised are used

winCTdictClusterShapes = generateConcaveHulls(winCTdictTimes, winCTdictClusters, winCTdictPointers)

####REPEAT FOR COUNTER TERRORISTS WINNING TEAM:

lossCTdictClusters = generateClusters(lossCTdictTimes)
lossCTdictClusterWinRate = findClusterWinRates(lossCTdictTimes, lossCTdictClusters, lossCTdictPointers)

for time in lossCTdictTimes.keys():
    for n in range(0, len(lossCTdictClusters[time])):
        lossCTdictPointers[time][n]['cluster'] = int(lossCTdictClusters[time][n]) #need to convert to int otherwise numpy.int64 which can't be JSON serialised are used

lossCTdictClusterShapes = generateConcaveHulls(lossCTdictTimes, lossCTdictClusters, lossCTdictPointers)

#WRITE TO FILES:

print("CT: Finished finding cluster shapes")
    
dictClusterWinRate = {'win': {2: winTdictClusterWinRate, 3: winCTdictClusterWinRate}, 'loss': {2: lossTdictClusterWinRate, 3: lossCTdictClusterWinRate}}
dictPointers = {'win': {2: winTdictPointers, 3: winCTdictPointers}, 'loss': {2: lossTdictPointers, 3: lossCTdictPointers}}
dictClusterShapes = {'win': {2: winTdictClusterShapes, 3: winCTdictClusterShapes}, 'loss': {2: lossTdictClusterShapes, 3: lossCTdictClusterShapes}}

with open('clusterWinRates.json', 'w') as fp:
    json.dump(dictClusterWinRate, fp)

with open('clusterPositions.json' ,'w') as fp:
    json.dump(dictPointers, fp)

with open('clusterShapes.json', 'w') as fp:
    json.dump(dictClusterShapes, fp)
    
print("Finished writing to files")

