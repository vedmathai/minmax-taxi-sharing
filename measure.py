import csv
import geopy.distance
import matplotlib.pyplot as plt


def findValue(alltimes, trips):
    distance = 0
    times = 0
    distances = []
    timeslist = []
    for time in alltimes:
        for trip in trips:
            if time in trips[trip] and time+30 in trips[trip]:
                distance += dist(trips[trip][time],trips[trip][time+30])
                times+=1
        distances += [distance]
        timeslist += [times]
    return distances, timeslist
def dist(c1, c2):
    return geopy.distance.vincenty(c1, c2).km
f = open('processedData.csv', 'rb')
reader = csv.reader(f,delimiter='\t')
alltimes = set()
trips={}
taxis =set()
for row in reader:
    taxis.add(row[0][10:])
    if row[0] not in trips:
        trips[row[0]]={}
    if int(row[2]) not in trips[row[0]]:
        trips[row[0]][int(row[2])]=(float(row[3]), float(row[4]))
    alltimes.add(int(row[2]))
print len(trips.keys())
dists1, times1 = findValue(sorted(list(alltimes)), trips)
print len(taxis)
f2 = open('newTrips.csv', 'rb')
reader = csv.reader(f2, delimiter = '\t')
newAlltimes = set()
trips = {}
for row in reader:
    if row[1] not in trips:
        trips[row[1]]={}
    if int(row[0]) not in trips[row[1]]:
        trips[row[1]][int(row[0])]=(float(row[2]), float(row[3]))
    newAlltimes.add(int(row[0]))
dists2, times2= findValue(sorted(list(newAlltimes)), trips)
for i in range(len(dists2)):
    if i %25 ==0:
        print i, dists1[i], dists2[i], times1[i], times2[i]
plt.plot(dists1, 'r')

plt.plot(dists2, 'g')
plt.ylabel('Total Distance Travelled in km')
plt.xlabel('Timestep')
plt.show()
plt.ylabel('Total time spent by travellers')
plt.xlabel('Timestep')
plt.plot(times1, 'r')
plt.plot(times2, 'g')
plt.show()
