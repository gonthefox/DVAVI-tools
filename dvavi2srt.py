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

global offset
global reminder

LOGFILE_NAME = 'logging.out'
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename=LOGFILE_NAME,
                    filemode='w')

# Sizeはデータフィールドの大きさであり、FourCC, Sizeを含まない
class Chunk(Structure):
    _fields_ = (
        ('ID', c_char * 4),
        ('Size', c_uint32),
        ('FourCC', c_char *4)
        )

class StreamHeader(Structure):
    _fields_ = (
        ('ID', c_char * 4),
        ('Size', c_uint32),
        ('fccType', c_char * 4),
        ('fccHandler', c_char * 4)        
        )

class AVIHeader(Structure):
    _fields_ = (
        ('ID', c_char * 4),
        ('Size', c_uint32),
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

# 80 Bytes    
class PDIF(Structure):
    _fields_ = (
        ('ID', c_ubyte * 3),
        ('PACK',PACK * 15),
        ('Dummy',c_ubyte * 2)
    )

# 480 Bytes = 6 PDIF
class SYSTEM(Structure):
    _fields_ = (
        ('HEADER', PDIF),
        ('SUBCODE', PDIF * 2),
        ('VAUX',PDIF * 3)
    )
    
# 80 Bytes    
class DIF(Structure):
    _fields_ = (
        ('ID', c_ubyte * 3),
        ('Payload', c_ubyte * 77)
    )

# 150*80 = 12,000 Bytes    
class SEQ(Structure):
    _fields_ = (
        ('DIF', DIF * 150),        
        ('dum', c_ubyte * 0)
        )
# 120,000 Bytes
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
    
FORMAT = "0x%08x %s (0x%08x) %s"
STRH   = "fccType: %s fccHandler: %s"
AVIH   = "dwTotalFrames: %d dwInitialFrames: %d"
LOAD  = "Total Bytes: %s ID:%s Size: (0x%08x)"

def base(data):

    pack13 = PACK(0x13)
    pack62 = PACK(0x62)
    pack63 = PACK(0x63)

    buffer = io.BytesIO(data)

    # RIFF AVI
    offset = 0
    riff   = Chunk()
    buffer.seek(offset)
    buffer.readinto(riff)

    logging.debug(FORMAT % (offset, riff.ID, riff.Size, riff.FourCC))    
    print(FORMAT % (offset, riff.ID, riff.Size, riff.FourCC))            
    
    offset += 12
    chunk = Chunk()
    buffer.seek(offset)
    buffer.readinto(chunk)

    logging.debug(FORMAT % (offset, chunk.ID, chunk.Size, chunk.FourCC))        
    print(FORMAT % (offset,chunk.ID, chunk.Size, chunk.FourCC))            
    
    movi = None
    if not chunk.ID == b'LIST':
        raise Exception("The first LIST not found.")

    while(True):
        if chunk.FourCC == b'movi':
            movi = chunk

            break
        else:
            offset += chunk.Size + 8
            buffer.seek(offset)
            buffer.readinto(chunk)
            
    logging.debug(FORMAT % (offset, movi.ID, movi.Size, movi.FourCC))    
    print(FORMAT % (offset, movi.ID, movi.Size, movi.FourCC))

    offset += 12
    chunk = Chunk()
    buffer.seek(offset)
    buffer.readinto(chunk)

    logging.debug(FORMAT % (offset, chunk.ID, chunk.Size, ""))        
    print(FORMAT % (offset, chunk.ID, chunk.Size, ""))

    base_offset = offset
    print("base: %x" % base_offset)
    while(chunk.ID != b'idx1'):
        logging.debug(FORMAT % (offset, chunk.ID, chunk.Size, ""))
        base_offset += 8        
        if chunk.ID == b'00db':
            system={}
            timecode = None            
            for i in range(0,10):
                system[i] = SYSTEM()
                offset = base_offset + sizeof(PDIF*150*i)
                buffer.seek(offset)
                buffer.readinto(system[i])

            pack13 = extractPack0x13(system)
            pack63 = extractPack0x63(system)
            pack62 = extractPack0x62(system)

            print(printRecdate(pack62), printRectime(pack63), printTimecode(pack13))

            rdfile.write("%s %s\n" % (printRecdate(pack62), printRectime(pack63)))
            tcfile.write("%s\n" % printTimecode(pack13))

        base_offset += chunk.Size
        chunk = Chunk()        
        buffer.seek(base_offset)
        buffer.readinto(chunk)
    return

def extractPack0x13(system):
    pack13 = PACK(0x13)
    for i in range(0,10):
        for j in range(0,2):
            for k in range(0,15):
                pack     = system[i].SUBCODE[j].PACK[k]
                packID = pack.packID()
                if packID == 0x13:
                    if not pack.DATA[4] == 0xff:
                        pack13 = pack
    return pack13

def extractPack0x63(system):
    pack63 = PACK(0x63)
    for i in range(0,10):
        for j in range(0,3):
            for k in range(0,15):
                pack     = system[i].VAUX[j].PACK[k]
                packID = pack.packID()
                if packID == 0x63:
                    if not pack.DATA[4] == 0xff:
                        pack63 = pack
    return pack63

def extractPack0x62(system):
    pack62 = PACK(0x62)
    for i in range(0,10):
        for j in range(0,3):
            for k in range(0,15):
                pack     = system[i].VAUX[j].PACK[k]
                packID = pack.packID()
                if packID == 0x62:
                    if not pack.DATA[4] == 0xff:
                        pack62 = pack
    return pack62

if __name__ == '__main__':

    parser= argparse.ArgumentParser(description="DVAVI2SRT")

    parser.add_argument('-a', '--avifile', help='DV-AVI input file name')
    parser.add_argument('-r', '--rdfile',   help='RECDATE output filename')
    parser.add_argument('-t', '--tcfile',   help='TIMECODE output filename')        
    args = parser.parse_args()

    # read an AVI file from the standard input
    data = None
    with open(args.avifile,'rb') as file:
        data = file.read()

    rdfile = open(args.rdfile,'w')
    tcfile = open(args.tcfile,'w')     
        
    if data == None:
        raise Exception("No AVI file specified.")

    base(data)

    rdfile.close()
    tcfile.close()
                
