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

#クラス内に可変長配列を定義できないのでトリックを使う
def base_old(data):
    global reminder, offset
    buffer = io.BytesIO(data)        
        
    # RIFF AVI
    offset = 0
    riff   = Chunk()
    buffer.seek(offset)
    buffer.readinto(riff)

    logging.debug("RIFF AVI")        
    logging.debug(FORMAT % (offset, riff.ID, riff.Size, riff.FourCC))
    logging.debug("0x%08x" % int(sizeof(riff) - 12))            

    #LIST hdrl Header List
    offset += 12
    hdrl   = Chunk()    
    buffer.seek(offset)
    buffer.readinto(hdrl)
    logging.debug("LIST Header")            
    logging.debug(FORMAT % (offset, hdrl.ID, hdrl.Size, hdrl.FourCC))
    logging.debug("0x%08x" % int(sizeof(hdrl) - 12))            

    #AVIH AVI Header
    offset += 12
    avih   = AVIHeader()    
    buffer.seek(offset)
    buffer.readinto(avih)
    logging.debug("AVI Header")            
    logging.debug(FORMAT % (offset, avih.ID, avih.Size, ""))
    logging.debug(AVIH % (avih.dwTotalFrames, avih.dwInitialFrames))    
    logging.debug("0x%08x" % int(sizeof(avih) - 12))            

    #LIST STRL Stream List
    offset += avih.Size + 8
    liststrl1   = Chunk()    
    buffer.seek(offset)
    buffer.readinto(liststrl1)
    logging.debug("STREAM List")            
    logging.debug(FORMAT % (offset, liststrl1.ID, liststrl1.Size, liststrl1.FourCC))
    logging.debug("0x%08x" % int(sizeof(liststrl1) - 12))            

    #STRH Stream Header (video)
    offset += 12
    strh   = StreamHeader()    
    buffer.seek(offset)
    buffer.readinto(strh)
    logging.debug("Stream Header")            
    logging.debug(FORMAT % (offset, strh.ID, strh.Size, strh.fccType))
    logging.debug("0x%08x" % int(sizeof(strh) - 12))            

    #STRF Stream format (video)
    offset += strh.Size + 8
    test   = Chunk()    
    buffer.seek(offset)
    buffer.readinto(test)
    logging.debug("Stream format")            
    logging.debug(FORMAT % (offset, test.ID, test.Size, ""))
    logging.debug("0x%08x" % int(sizeof(test) - 12))            

    #index
    offset += test.Size + 8
    test   = Chunk()    
    buffer.seek(offset)
    buffer.readinto(test)
    logging.debug("LIST Stream list")            
    logging.debug(FORMAT % (offset, test.ID, test.Size, ""))
    logging.debug("0x%08x" % int(sizeof(test) - 12))            

    #Stream Header
    offset += test.Size + 8
    liststrl2   = Chunk()    
    buffer.seek(offset)
    buffer.readinto(liststrl2)
    logging.debug("LIST Stream")            
    logging.debug(FORMAT % (offset, liststrl2.ID, liststrl2.Size, liststrl2.FourCC))
    logging.debug("0x%08x" % int(sizeof(liststrl2) - 12))            

    #STRH Stream Header (audio)
    offset += 12
    strh2   = StreamHeader()    
    buffer.seek(offset)
    buffer.readinto(strh2)
    logging.debug("Stream Header")            
    logging.debug(FORMAT % (offset, strh2.ID, strh2.Size, strh2.fccType))
    logging.debug("0x%08x" % int(sizeof(strh2) - 12))            

    #STRF Stream format (audio)
    offset += strh2.Size + 8
    test   = Chunk()    
    buffer.seek(offset)
    buffer.readinto(test)
    logging.debug("LIST Stream")            
    logging.debug(FORMAT % (offset, test.ID, test.Size, ""))
    logging.debug("0x%08x" % int(sizeof(test) - 12))            

    #Stream header
    offset += test.Size + 8
    test   = Chunk()    
    buffer.seek(offset)
    buffer.readinto(test)
    logging.debug("stream header")            
    logging.debug(FORMAT % (offset, test.ID, test.Size, ""))
    logging.debug("0x%08x" % int(sizeof(test) - 12))            

    #Stream format
    offset += test.Size + 8
    test   = Chunk()    
    buffer.seek(offset)
    buffer.readinto(test)
    logging.debug("stream format")            
    logging.debug(FORMAT % (offset, test.ID, test.Size, test.FourCC))
    logging.debug("0x%08x" % int(sizeof(test) - 12))            

    #JUNK
    offset += test.Size + 8
    test   = Chunk()    
    buffer.seek(offset)
    buffer.readinto(test)
    logging.debug("junk")            
    logging.debug(FORMAT % (offset, test.ID, test.Size, ""))
    logging.debug("0x%08x" % int(sizeof(test) - 12))            

    #MOVI List ここから実データ
    offset += test.Size + 8
    test   = Chunk()    
    buffer.seek(offset)
    buffer.readinto(test)
    logging.debug("LIST movi")            
    logging.debug(FORMAT % (offset, test.ID, test.Size, test.FourCC))
    logging.debug("0x%08x" % int(sizeof(test) - 12))            

    offset += 12
#    test   = PackData()    
    buffer.seek(offset)
    buffer.readinto(test)
    logging.debug("PACK DATA")            
#    logging.debug(FORMAT % (offset, test.ID, test.Size, test.FourCC))
    logging.debug("0x%08x" % int(sizeof(test) - 12))            
    
    #idx1
    offset += test.Size + 8
    test   = Chunk()    
    buffer.seek(offset)
    buffer.readinto(test)
    logging.debug("idx1")            
    logging.debug(FORMAT % (offset, test.ID, test.Size, test.FourCC))
    logging.debug("0x%08x" % int(sizeof(test) - 12))            
    
    return
    
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
# FORMAT = "0x%08x %s (0x%08x)"
STRH   = "fccType: %s fccHandler: %s"
AVIH   = "dwTotalFrames: %d dwInitialFrames: %d"
LOAD  = "Total Bytes: %s ID:%s Size: (0x%08x)"

def process(test, offset):
    global reminder
    while reminder > 0:
        if test.FourCC in (b'LIST', b'RIFF'):
            logging.debug(FORMAT % (offset, test.FourCC, test.Size))
            offset   = offset + 12
            reminder = reminder - 12
            test = Chunk()
        else:
            logging.debug(FORMAT % (offset, test.FourCC, test.Size))
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
    while(offset<=0x82fde38):
        logging.debug(FORMAT % (offset, chunk.ID, chunk.Size, ""))
        print(FORMAT % (offset, chunk.ID, chunk.Size, ""))
        base_offset += 8        
        if chunk.ID == b'00db' or chunk.ID == b'01__' :
            block={}
            for i in range(0,10):
                for j in range(0,6):
                    k = i*6+j
                    block[k] = PDIF()
                    offset = base_offset + sizeof(PDIF*150*i)+sizeof(PDIF*j)
                    buffer.seek(offset)
                    buffer.readinto(block[k])

        base_offset += chunk.Size
        chunk = Chunk()        
        buffer.seek(base_offset)
        buffer.readinto(chunk)

    return


if __name__ == '__main__':

    parser= argparse.ArgumentParser(description="DVAVI2SRT")

    parser.add_argument('avifile', help='DV-AVI input file name')
#    parser.add_argument('-r','rdfile', help='RECDATE output filename')
#    parser.add_argument('-t','tcfile', help='TIMECODE output filename')        
    args = parser.parse_args()

    # read an AVI file from the standard input
    data = None
    with open(args.avifile,'rb') as file:
        data = file.read()
    
    if data == None:
        raise Exception("No AVI file specified.")

    base(data)
