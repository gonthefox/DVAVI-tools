#!/usr/bin/env python
#-*- coding: utf-8 -*-
# "dvavi2srt.py"

# DIF[0]: Header
# DIF[1]: Subcode(0)
# DIF[2]: Subcode(1)
# DIF[3]: VAUX(0)
# DIF[4]: VAUX(1)
# DIF[5]: VAUX(2)
# time  code    0x13
# video recdate 0x62
# video rectime 0x63

from ctypes import *
import io
import sys
import logging, argparse

global reminder

LOGFILE_NAME = 'logging.out'
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename=LOGFILE_NAME,
                    filemode='w')

class Chunk(Structure):
    _fields_ = (
        ('FourCC', c_char * 4),
        ('Size', c_uint32),
        ('Type', c_char * 4)
        )

class StreamHeader(Structure):
    _fields_ = (
        ('fccType', c_char * 4),
        ('fccHandler', c_char * 4)        
        )

class AVIHeader(Structure):
    _fields_ = (
        ('dwMicroSecPerFrame', c_uint32),
        ('dwMaxBytesPerSec', c_uint32),
        ('dwPaddingGranularity', c_uint32),
        ('dwFlags', c_uint32),
        ('dwTotalFrames', c_uint32),
        ('dwInitialFrames', c_uint32)
        )
    
class PACK(Structure):
    _fields_ = (
        ('DATA', c_ubyte * 5),
    )
    def __init__(self, packid):
        self.DATA[0] = packid
        for i in range(1,5):
            self.DATA[i] = 0xff
        
    def getData(self):
        return (self.DATA[0], self.DATA[1], self.DATA[2],self.DATA[3],self.DATA[4])
    def packID(self):
        return self.DATA[0]

    def packData(self):
        return (self.DATA[1], self.DATA[2],self.DATA[3],self.DATA[4])      

class PDIF(Structure):
    _fields_ = (
        ('ID', c_ubyte * 3),
        ('PACK',PACK * 15),
        ('Dummy',c_ubyte * 2)
    )
    
class DIF(Structure):
    _fields_ = (
        ('ID', c_ubyte * 3),
        ('Payload', c_ubyte * 77)
    )

class SEQ(Structure):
    _fields_ = (
        ('DIF', DIF * 150),        
        ('dum', c_ubyte * 0)
        )

class FRAME(Structure):
    _fields_ = (
        ('SEQ', SEQ * 10),        
        ('dum', c_ubyte * 0)
        )    

    
def printTimecode(pack12):
    if (pack12.DATA[1],pack12.DATA[2],pack12.DATA[3],pack12.DATA[4]) == (0xff,0xff,0xff,0xff):
        return "%02s:%02s:%02s %02s" % ('--', '--', '--', '--')
    else:
        hour    = (pack12.DATA[4]>>4 & 0x03)*10+(pack12.DATA[4] & 0x0f)
        minute  = (pack12.DATA[3]>>4 & 0x07)*10+(pack12.DATA[3] & 0x0f)
        second  = (pack12.DATA[2]>>4 & 0x07)*10+(pack12.DATA[2] & 0x0f)
        frame   = (pack12.DATA[1]>>4 & 0x03)*10+(pack12.DATA[1] & 0x0f)        
        return "%02d:%02d:%02d %02d" % (hour, minute, second, frame)

def printRectime(pack12):
    hour    = (pack12.DATA[4]>>4 & 0x03)*10+(pack12.DATA[4] & 0x0f)
    minute  = (pack12.DATA[3]>>4 & 0x07)*10+(pack12.DATA[3] & 0x0f)
    second  = (pack12.DATA[2]>>4 & 0x07)*10+(pack12.DATA[2] & 0x0f)    
    return "%02d:%02d:%02d" % (hour, minute, second)


def printRecdate(pack11):
    year = (pack11.DATA[4]>>4 & 0x0f)*10+(pack11.DATA[4] & 0x0f)

    if year>50:
        year = year + 1900
    else:
        year = year + 2000

    month = ((pack11.DATA[3]>>4) & 0x01)*10+(pack11.DATA[3] & 0x0f)
    dom   = ((pack11.DATA[2]>>4) & 0x03)*10+(pack11.DATA[2] & 0x0f)    
    dow   = ((pack11.DATA[3]>>5) & 0x07)    
    dows  = ['SUN','MON','TUE','WED','THU','FRI','SAT','UNKNOWN']

    if not dow == 0x07:
        return "%04d-%02d-%02d (%s)" % (year, month, dom, dows[dow])
    else:
        return "%04d-%02d-%02d" % (year, month, dom)        
    
def getPackData(offset):
    pack13 = PACK(0x13)
    pack62 = PACK(0x62)
    pack63 = PACK(0x63)
    block={}
    for i in range(0,10):
        for j in range(0,6):
            k = i*6+j
            block[k] = PDIF()
            buffer.seek(offset+sizeof(PDIF*150*i)+sizeof(PDIF*j))
            buffer.readinto(block[k])

    for i in range(0,60):
        for n  in range(0,15):
            pack      =  block[i].PACK[n]
            packID    =  pack.packID()
            packDATA  =  pack.packData()            

            if not packDATA == (0xff,0xff,0xff,0xff):
                if packID == 0x13:
                    pack13 = pack
                if packID == 0x62:
                    pack62 = pack
                if packID == 0x63:
                    pack63 = pack

    print(printRecdate(pack62), printRectime(pack63), printTimecode(pack13))    
                    
FORMAT = "0x%08x %s (0x%08x) %s"
STRH   = "fccType: %s fccHandler: %s"
AVIH   = "dwTotalFrames: %d dwInitialFrames: %d"
def process(test, offset):
    global reminder
    while reminder > 0:
        if test.FourCC in (b'LIST', b'RIFF'):
            logging.debug(FORMAT % (offset, test.FourCC, test.Size, test.Type))
            offset   = offset + 12
            reminder = reminder - 12
            test = Chunk()
        else:
            logging.debug(FORMAT % (offset, test.FourCC, test.Size, ''))
            if test.FourCC == b'strh':
                strh = StreamHeader()
                buffer.seek(offset+8)
                buffer.readinto(strh)
                logging.debug(STRH % (strh.fccType, strh.fccHandler))
                if strh.fccType == b'iavs':
                    logging.debug('DV-AVI Type-1 detected.')
                elif strh.fccType == b'vids':
                    logging.debug('DV-AVI Type-2 detected.')
                else:
                    pass

            if test.FourCC == b'avih':
                avih = AVIHeader()
                buffer.seek(offset+8)
                buffer.readinto(avih)
                logging.debug(AVIH % (avih.dwTotalFrames, avih.dwInitialFrames))
                
            if test.FourCC == b'00db' or test.FourCC == b'00__' :
                # skip 8 bytes for the FourCC and the size
                getPackData(offset+8)
            offset   = offset   + test.Size + 8
            reminder = reminder - test.Size - 8
        buffer.seek(offset)
        buffer.readinto(test)
        if test.FourCC in (b'LIST',b'RIFF'):
            process(test, offset)
    return

def base():
    
    global reminder
    test   = Chunk()
    offset = 0
    buffer.readinto(test)

    print("Check the header: %s" % test.FourCC)
    if not test.FourCC == b'RIFF':
        raise Exception("Not a RIFF file.")

    reminder = test.Size + 8
    process(test, offset)
    return

if __name__ == '__main__':

    parser= argparse.ArgumentParser(description="DVAVI2SRT")

    parser.add_argument('avifile')
    args = parser.parse_args()

    # read an AVI file from the standard input
    file = open(args.avifile,'rb')
    data = file.read()
    
    if data == None:
        raise Exception("No AVI file specified.")

    buffer = io.BytesIO(data)
    base()
