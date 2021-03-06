#!/usr/bin/env python

"""
jmyers

this script looks at the runlogs generated by CPP linkTracklets
(provided it's configured correctly), confers with the database, and
determines how much total time was spent processing per start image;
that is, using the time spent on every pair of first/last endpoint
images, find out how much total time was spent on each given first
endpoint image.

We expect items to look like: 
Looking for tracks between images at times 49543.427347999997 (image 0 / 63) and 49552.254621000000 (image 1 / 63)  (with 0 support images).
 current wall-clock time is Tue Apr  5 17:34:19 2011
That iteration took 0.000000000000 seconds. 
 so far, we have found 0 tracks.


New version also returns number of tracks found per start image.
"""



import sys
import MySQLdb as db

EPSILON=1e-6 


DB_HOST="localhost"
DB_USER="jmyers"
DB_PASS="jmyers"
OPSIM_DB="opsim_3_61"
OPSIM_TABLE="output_opsim3_61"


def increment(d, key, value):
    """ if dict d has an entry at key, add value to it. otherwise set
    d[key] = value.  Return d."""
    if d.has_key(key):
        d[key] += value
    else:
        d[key] = value
    return d
    

def obsHistFromStartTime(knownImages, startTime, curs):
    """ find the obsHistId of the image which happened at about
    ~startTime and return it.  Use the knownImages map if possible but
    failing that use the DB and update knownImages."""
    # using a float as a key is bad but we have a backup if the lookup
    # fails.
    if knownImages.has_key(startTime):
        return knownImages[startTime]
    # try SQL instead
    sql = """ SELECT obsHistId FROM %s WHERE expMjd > %f AND expMjd < %f GROUP BY expMjd;"""\
        % (OPSIM_TABLE, startTime - EPSILON, startTime + EPSILON)
    curs.execute(sql)
    res = curs.fetchall()
    if len(res) != 1:
        print res
        print sql
        raise Exception("Got multiple images at given start time %f?!" % \
                            startTime)
    obsHist = res[0][0]
    knownImages[startTime] = obsHist
    return obsHist



def getPerStartImageRuntimesAndTrackCounts(runlog, curs):
    """ reads runlog (an open file), consults DB via cursor, and
    returns a dict from obsHistId -> total runtime processing each
    first endpoint image seen."""
    runtimeStats = {}
    trackCountStats = {}
    
    curStartImageTime = None
    line = runlog.readline()
    knownImages = {}
    tracksSoFar = 0
    
    while line != "":
        items = line.split()
        if len(items) > 1:
            if items[0:2] == ["Looking", "for"]:
                curStartImageTime = float(items[7])
            if items[0:2] == ["That", "iteration"]:
                if curStartImageTime == None:
                    raise Exception("Error parsing runlog")
                runtime = float(items[3])
                obsHist = obsHistFromStartTime(knownImages, 
                                               curStartImageTime,
                                               curs)
                increment(runtimeStats, obsHist, runtime)
            if items[0:2] == ["so", "far"]:
                tracksFound = int(items[5])
                dTracks = tracksFound - tracksSoFar
                tracksSoFar = tracksFound
                obsHist = obsHistFromStartTime(knownImages, 
                                               curStartImageTime,
                                               curs)                
                increment(trackCountStats, obsHist, runtime)
                
        line = runlog.readline()
    return stats



def writeStats(stats1, stats2, outfile):
    """ write stats to outfile."""
    for obsHist in stats1.keys():
        outfile.write("%d %10f %d\n" % (obsHist, stats1[obsHist], stats2[obsHist]))



if __name__=="__main__":
    conn = db.connect(user=DB_USER, passwd=DB_PASS, host=DB_HOST, 
                      db=OPSIM_DB)
    curs = conn.cursor()
    runlog = file(sys.argv[1],'r')
    outfile = file(sys.argv[2],'w')

    runtimeStats, trackCountStats = getPerStartImageRuntimesAndTrackCounts(runlog, curs)

    writeStats(runtimeStats, trackCountStats, outfile)
    
