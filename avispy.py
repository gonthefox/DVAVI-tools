#!/usr/bin/env python
#-*- coding: utf-8 -*-
# "avispy.py"

# DIF[0]: Header
# DIF[1]: Subcode(0)
# DIF[2]: Subcode(1)
# DIF[3]: VAUX(0)
# DIF[4]: VAUX(1)
# DIF[5]: VAUX(2)

BLK=80
SEQ=12000

from ctypes import *
import io
import sys
import logging

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


class PACK(Structure):
    _fields_ = (
        ('DATA', c_ubyte * 5),
    )
    def getData(self):
        return (self.DATA[0], self.DATA[1], self.DATA[2],self.DATA[3],self.DATA[4])

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
    
    
def printData(offset):
    vaux2  = PDIF()
    buffer.seek(offset+sizeof(PDIF*5))
    buffer.readinto(vaux2)

    print printRecdate(vaux2.PACK[11]), printRectime(vaux2.PACK[12]),    

    sc0     = PDIF()
    sc1     = PDIF()
    buffer.seek(offset+sizeof(PDIF*1))
    buffer.readinto(sc0)
    buffer.seek(offset+sizeof(PDIF*2))
    buffer.readinto(sc1)
    print  printTimecode(sc0.PACK[7])
#    print "%02X %02X%02X%02X%02X" % sc0.PACK[7].getData()    

FORMAT = "0x%08x %s (0x%08x) %s"

def process(test, offset):
    global reminder
    while reminder > 0:
        if test.FourCC in ('LIST','RIFF'):
            logging.debug(FORMAT % (offset, test.FourCC, test.Size, test.Type))
            offset   = offset + 12
            reminder = reminder - 12
            test = Chunk()
        else:
            logging.debug(FORMAT % (offset, test.FourCC, test.Size, ''))
            if test.FourCC == '00db':
                printData(offset+8)
            offset   = offset   + test.Size + 8
            reminder = reminder - test.Size - 8
        buffer.seek(offset)
        buffer.readinto(test)
        if test.FourCC in ('LIST','RIFF'):
            process(test, offset)
    return

if __name__ == '__main__':

    global reminder
    
    data   = sys.stdin.read()   # read an AVI file from the standard input

    if data == None:
        raise Exception("No AVI file specified.")

    buffer = io.BytesIO(data)

    test   = Chunk()
    offset = 0
    buffer.readinto(test)

    if not test.FourCC == 'RIFF':
        raise Exception("Not a RIFF file.")

    reminder = test.Size + 8
    process(test, offset)
