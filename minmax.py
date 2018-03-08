AVG_SPEED = 0.226 #In Kms per 30 seconds
MAX_DEPTH = 3 #The max depth of the game tree
PASS_TRAV_PERC=.3 #The percentage excess that a rider is allowed to travel over her existing ride.

import csv
import copy
import ast
import geopy.distance
from itertools import chain, combinations

#Helper function to find the distance in km between two geographical lat long locations
def dist(c1, c2):
    return geopy.distance.vincenty(c1, c2).km

def powerset(iterable):
    "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))

#Helper function to interpolate the position of a car between any two points
def interpolate(c1, c2):
    distance = dist(c1, c2)
    ntimesteps = int(distance/AVG_SPEED)+0.0001
    xslope = float(c2[0]-c1[0])/ntimesteps
    yslope = float(c2[1]-c1[1])/ntimesteps
    ntimesteps = int(ntimesteps)
    path = []
    for n in range(1, ntimesteps+1):
        xdel = c1[0]+n*xslope
        ydel = c1[1]+n*yslope
        path+=[(xdel, ydel)]
    return path

#Helper function to read the data into pertinent datastructures
def getData(fi):
    f = open(fi, 'rb')
    reader = csv.reader(f,delimiter='\t')
    tripset = {}
    tripset2 = {}
    timeset = set()
    for row in reader:
        trip = int(row[0])
        taxi = int(row[1])
        time = int(row[2])
        position = (float(row[3]), float(row[4]))
        timeset.add(time)
        if taxi not in tripset:
            tripset[taxi] = {}
        if trip not in tripset[taxi]:
            tripset2[trip] = {}
            tripset[taxi][trip]={}
        tripset[taxi][trip][time]=position
    taxitimetrip = {}
    for taxi in tripset:
        taxitimetrip[taxi] = {}
        for trip in tripset[taxi]:
            for time in sorted(tripset[taxi][trip].keys()):
                tripset2[trip][time]=tripset[taxi][trip][time]
                taxitimetrip[taxi][time] = trip
    times = sorted(list(timeset))
    return times, tripset2, taxitimetrip

#Helper function to the distance between every combination of taxis
def find_taxi_taxi_distance(taxitimetrip, tripset, time):
    distances = {}
    minminmappings = set()
    for taxi1 in taxitimetrip:
        mintaxi=''
        mindist = float('inf')
        if time not in taxitimetrip[taxi1]:
            continue
        trip1 = taxitimetrip[taxi1][time]
        c1 = tripset[trip1][time]
        for taxi2 in taxitimetrip:
            if taxi1==taxi2:
                continue
            if time not in taxitimetrip[taxi2]:
                continue
            trip2 = taxitimetrip[taxi2][time]
            c2 = tripset[trip2][time]
            d = dist(c1, c2)
            if d<mindist:
                mintaxi = taxi2
                mindist = d
        minminmappings.add((taxi1, mintaxi))
        if (mintaxi,taxi1) in minminmappings:
            if mintaxi not in distances:
                distances[mintaxi]= {}
            if taxi1 not in distances:
                distances[taxi1]={}
            distances[taxi1][mintaxi]=mindist
            distances[mintaxi][taxi1]=mindist
    return distances

#Heloer function that performs the transfer of the trip from one car to the other.
def transfer_trip(timestep, tripset, taxitimetrip, percent1, percent2, taxi1, taxi2):
    if percent1> percent2:
        taxi1, taxi2 = taxi2, taxi1
        percent1, percent2 = percent2, percent1
    maintaxi = taxi1
    updatedTrips = set()
    trip1 = taxitimetrip[taxi1][timestep]
    trip2 = taxitimetrip[taxi2][timestep]
    tripos1 = tripset[trip1]
    tripos2 = tripset[trip2]
    triptimes1 = sorted([time for time in tripset[trip1].keys() if time >= timestep])
    triptimes2 = sorted([time for time in tripset[trip2].keys() if time >= timestep])
    tripdel1 = interpolate(tripos2[triptimes2[0]], tripos1[triptimes1[0]])
    tripdel2 = interpolate(tripos1[triptimes1[-1]], tripos2[triptimes2[-1]])
    startpoint2 = tripos2[triptimes2[0]]
    startpoint1 = tripos1[triptimes1[0]]
    endpoint2 = tripos2[triptimes2[-1]]
    tripos2={}
    ### for car 2 ###
    for time in tripset[trip2]:
        if time < timestep:
            tripos2[time]=tripset[trip2][time]

    tripos2[timestep] = startpoint2
    for posi, pos in enumerate(tripdel1):
        tripos2[timestep+(posi)*30] = pos
    for time in  range(timestep+(len(tripdel1))*30, triptimes2[-1]+30, 30):
        if taxi2 in taxitimetrip:
            if time in taxitimetrip[taxi2]:
                del(taxitimetrip[taxi2][time])

    ###  for car1  ####
    for posi, pos in enumerate(tripdel2):
        tripos1[triptimes1[-1]+(posi+1)*30] = pos
    moveby = len(tripdel1)
    for i in range(moveby):
        if triptimes1[-1]-(i*30) in tripos1:
            tripos1[triptimes1[-1]-(i+moveby)*30] = tripos1[triptimes1[-1]-i*30]
    for posi, pos in enumerate(tripdel1):
        tripos1[triptimes1[0]+(posi*30)]=startpoint1
    tripset[trip1] = tripos1
    tripset[trip2] = tripos2
    updatedTrips.add(trip1)
    if percent1> percent2:
        tripset[trip1], tripset[trip2] = tripset[trip2], tripset[trip1]
    return tripset, taxitimetrip, maintaxi, updatedTrips, tripdel2

#Help function that finds the value of each state.
def measureStates(combinations, states, timestepcount, timestep, tripset, taxitimetrip, tripdels, depth):
    combinations = list(powerset(combinations))
    cartimes = []
    print 'The number of combinations are', len(combinations), 'at depth', depth
    mincartime = float('inf')
    mindistance = float('inf')
    mintotaltime = float('inf')
    for combination in combinations:
        #print combination
        tripset2 = copy.deepcopy(tripset)
        taxitimetrip2 = copy.deepcopy(taxitimetrip)
        maintaxi = set()
        updatedTrips=set()

        fromBelow  = []

        for pair in combination:
            maintaxi.add(pair[0])
            tripsetPair, taxitimetripPair, updatedTripsi = states[pair][0]
            updatedTrips|=updatedTripsi
            taxitimetrip2[pair[0]]=taxitimetripPair[pair[0]]
            taxitimetrip2[pair[1]]=taxitimetripPair[pair[1]]
            for time in taxitimetrip2[pair[0]]:
                trip = taxitimetrip2[pair[0]][time]
                tripset2[trip] = tripsetPair[trip]
            for time in taxitimetrip2[pair[1]]:
                trip = taxitimetrip2[pair[1]][time]
                tripset2[trip] = tripsetPair[trip]

        totaltime = 0
        totalcartime =0
        totaldistance = 0
        allTrips = set()
        for taxi in taxitimetrip2:
            for time in taxitimetrip2[taxi]:
                trip = taxitimetrip2[taxi][time]
                allTrips.add(trip)
        for trip in allTrips:
            totaltime+=len([t for t in tripset2[trip] if t>=timestep])

            totalcartime+=len([t for t in tripset2[trip] if t>=timestep])
            prevloc = (0,0)
            for timei, time in enumerate(sorted(tripset2[trip].keys())):

                if timei ==0:
                    prevloc = tripset2[trip][time]
                    continue
                if time<timestep:
                    continue
                totaldistance+=dist(tripset2[trip][time], prevloc)
                prevloc = tripset2[trip][time]
            if trip in updatedTrips:
                totaltime+=len([t for t in tripset2[trip] if t>=timestep])
                totaltime -= len(tripdels[pair[0]])
        if totaltime<mintotaltime:
            maxtaxitimetrip = copy.deepcopy(taxitimetrip2)
            maxtripset = copy.deepcopy(tripset2)
            mincartime = totalcartime
            mintotaltime = totaltime
            mindistance = totaldistance

        if depth < MAX_DEPTH:
            callWork = work( timestepcount, timestep, tripset, taxitimetrip, depth )
            callWork = list(callWork)
            callWork[5]=updatedTrips
            fromBelow+=[callWork]
    if depth>=MAX_DEPTH:
        return  (maxtaxitimetrip, maxtripset, mincartime, mintotaltime, mindistance, updatedTrips)
    else:
        if len(fromBelow)>0:
            return sorted(fromBelow, key = lambda x: x[2], reverse=False)[0]
        else:
            allTrips = set()
            totalcartime =0
            totaldistance = 0
            for taxi in taxitimetrip:
                for time in taxitimetrip[taxi]:
                    trip = taxitimetrip[taxi][time]
                    allTrips.add(trip)
            for trip in allTrips:
                prevloc = (0,0)
                for timei, time in enumerate(sorted(tripset2[trip].keys())):
                    if timei ==0:
                        prevloc = tripset2[trip][time]
                        continue
                    if time<timestep:
                        continue
                    totaldistance+=dist(tripset2[trip][time], prevloc)
                    prevloc = tripset2[trip][time]
                totalcartime += len(tripset[trip].keys())
            return (taxitimetrip, tripset, totalcartime, totalcartime, totaldistance, set())

#The main function that calls the measureStates function and along with that function creates the game states for the next level
def work(timestepcount, timestep, tripset, taxitimetrip, depth = 0):
    distances = find_taxi_taxi_distance(taxitimetrip, tripset, timestep)
    states = {}
    combinations= set()
    tripdels = {}
    for taxi1 in distances:
        for taxi2 in distances[taxi1]:
            if timestep not in taxitimetrip[taxi1] or timestep not in taxitimetrip[taxi2]:
                continue
            if depth!=0: #Cannot check taxis that haven't started as yet
                if timestep-depth*30*4 not in taxitimetrip[taxi1] or timestep-depth*30*4 not in taxitimetrip[taxi2]:
                    continue
            trip1 = taxitimetrip[taxi1][timestep]
            trip2 = taxitimetrip[taxi2][timestep]
            tripos1 = tripset[trip1]
            tripos2 = tripset[trip2]
            initialdistance = distances[taxi1][taxi2]
            triptimes1 = sorted(tripset[trip1].keys())
            triptimes2 = sorted(tripset[trip2].keys())
            trip1dist = dist(tripos1[triptimes1[0]], tripos1[triptimes1[-1]])
            trip2dist = dist(tripos2[triptimes2[0]], tripos2[triptimes2[-1]])
            distance = dist(tripos1[triptimes1[-1]], tripos2[triptimes2[-1]])
            percent1 = (distance+initialdistance)*1.0/(trip1dist+.1**7)
            percent2 = (distance+initialdistance)*1.0/(trip2dist+.1**7)
            if percent1<PASS_TRAV_PERC or percent2<PASS_TRAV_PERC:
                tripsetnew = copy.deepcopy(tripset)
                taxitimetripnew = copy.deepcopy(taxitimetrip)
                tripsetnew, taxitimetripnew, maintaxi, updatedTrips, tripdel2 = transfer_trip(timestep, tripsetnew, taxitimetripnew, percent1, percent2, taxi1, taxi2)
                tripdels[maintaxi] = tripdel2
                if taxi1 == maintaxi:
                    combination = (taxi1, taxi2)
                    combinations.add((combination))
                else:
                    combination = (taxi2, taxi1)
                    combinations.add((combination))
                states[combination] = [[tripsetnew, taxitimetripnew, updatedTrips]]

    return measureStates(combinations, states, timestepcount, timestep+30*4, tripset, taxitimetrip,tripdels, depth+1)

#The starting point of the program.
def main():
    times_list, tripset, taxitimetrip= getData('processedData.csv')
    newtaxitimetrip = {}
    newtripset = {}
    f = open('newTrips.csv', 'wb')
    writer = csv.writer(f, delimiter = '\t')
    for timestepcount, timestep in enumerate(times_list):
        print 'The time step Count', timestepcount
        taxitimetrip, tripset, mincartime, mintotaltime, mindistance, updatedTrips= work(timestepcount, timestep, tripset, taxitimetrip)
        for taxi in taxitimetrip:
            if taxi not in newtaxitimetrip:
                newtaxitimetrip[taxi]={}
            if timestep in taxitimetrip[taxi]:
                newtaxitimetrip[taxi][timestep]=taxitimetrip[taxi][timestep]
        for trip in tripset:

            newtripset[trip]={}
            if timestep in tripset[trip]:
                newtripset[trip][timestep] = tripset[trip][timestep]
                if trip in updatedTrips:
                    colour = 'red'
                else:
                    colour = 'blue'
                writer.writerow([str(timestep), str(trip), newtripset[trip][timestep][0], newtripset[trip][timestep][1] , colour])
        print '======'
if __name__ == '__main__':
    main()
