import csv
import numpy as np
import geopy.distance
import time
import datetime
import ast

START_DATE="08/09/2013" #Enter any date in the range 01/07/2013 to 30/06/2014
START_TIME_OFFSET = 0 #A number that will be mulitplied by 30 to get the number of seconds from the 12 am of the start date.
END_TIME_OFFSET =200 #A number that will be mulitplied by 30 to get the number of seconds from the 12 am of the start date.
SECONDS_PER_INTERVAL=30 #This has not been fully parameterized yet. It has been hardcoded to 30 in most places in the code.

def dist(c1, c2):
    return geopy.distance.vincenty(c1, c2).km
def inter(c1,c2, t):
    c0 = c1[0]*(15-t)+t*c2[0]
    c1 = c1[1]*(15-t)+t*c2[1]
    return (c0,c1)

if START_TIME_OFFSET>END_TIME_OFFSET:
    print 'START_TIME_OFFSET cannot be greater than END_TIME_OFFSET'
    exit()
s1 = START_DATE
t1 = time.mktime(datetime.datetime.strptime(s1, "%d/%m/%Y").timetuple())
t2 = t1 + END_TIME_OFFSET*SECONDS_PER_INTERVAL
t1 = t1 + START_TIME_OFFSET*SECONDS_PER_INTERVAL

trainfile = open('train.csv', 'rb') #The input file
traincsv = csv.reader(trainfile, delimiter = ',')

f = open('processedData1.csv', 'wb') #The output file
fcsv = csv.writer(f, delimiter = '\t')

allPoints = []
starts = {}
ends = {}
max_line_len = 0

for row in traincsv:
    try:
        int(row[5])
    except:
        continue
    if not t1<int(row[5])<t2:
        continue
    taxi = row[4]
    line = [(float(k[0]), float(k[1])) for k in ast.literal_eval(row[8])]
    max_line_len = max(max_line_len, len(line))
    if len(line)>0:
        starts[row[0]] = line[0]
        ends[row[0]] = line[-1]
    start = int(row[5])
    for ii in range(len(line)-1):
        for s in range(15):#print taxi, int(start)+15*ii, i
            allPoints += [[row[0], taxi, int(start)+15*ii+s, inter(line[ii], line[ii+1], s)]]
allPoints = sorted(allPoints, key=lambda x: (x[1], x[0], x[2]))
print 'Number of datapoints', len(allPoints)
allPoints = [i for i in allPoints if int(i[2])%SECONDS_PER_INTERVAL ==0]

for point in allPoints:
    fcsv.writerow([point[0], point[1], point[2], point[3][0], point[3][1]])
