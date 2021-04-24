#!/usr/bin/env python
import sys, datetime

t  = datetime.datetime(year=2000, month=1, day=1,hour=0, minute=0, second=0)
for i, line in enumerate(sys.stdin):
    if (i !=  0) and (i%30 == 0):
        t = t + datetime.timedelta(microseconds=1000000)
    print i
    print "%s,%s" % (t.time(),i%30*33),
    print '-->',
    print "%s,%s" % (t.time(),i%30*33+33)
    print line.split()[0], line.split()[1]
    print
