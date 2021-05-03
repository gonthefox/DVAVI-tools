#!/usr/bin/env python
import os, argparse
import glob
import dvavi2srt as dv

HANDBRAKE = """
HandBrakeCLI  -i %s \
	      --decomb -t 1 -c 1 -o %s \
	      -f m4v -e x264 -q 20 -b 1500 -2 -T -a 1 -E faac -B 160 -6 dpl2 -D 1 \
	      -x ref=2:bframes=2:me=umh -v -s 1,2 \
	      --srt-file "recdatetime.srt","timecode.srt" \
	      --srt-lang jpn --srt-default 1 \
"""

EXIFTOOL = 'exiftool -CreateDate="%s" -DateTimeOriginal="%s" %s'

if __name__ == '__main__':

    parser= argparse.ArgumentParser(description="DVAVITOOL")

    parser.add_argument('-i', '--indir',     help='directory which AVI files are contained')
    parser.add_argument('-o', '--outdir',  help='directory which MP4 files are generated in')
    args = parser.parse_args()

    if not os.path.exists(args.indir):
        raise Exception("Input directory not found.")

    avifiles = glob.glob(args.indir+"*.avi")

    for avifile in avifiles:
            data = None
            print(avifile)
            with open(avifile,'rb') as file:
                data = file.read()

            dv.rdfile = open("recdatetime.srt",'w')
            dv.tcfile = open("timecode.srt",'w')     

            offset = dv.find_movi(data)            
            recdatetime = dv.getRecdatetime(data, offset)            
            year    = str(recdatetime[0:4])
            month = str(recdatetime[6:7])
            day     = str(recdatetime[9:10])
            
            offset = dv.find_movi(data)
            dv.process(data, offset)

            dv.rdfile.close()
            dv.tcfile.close()

            filepath = args.outdir+"/"+year+"/"+month+"/"+day+"/"
            if not os.path.exists(filepath):
                os.makedirs(filepath)
            mp4file = filepath+os.path.splitext(os.path.basename(avifile))[0]+".mp4"
            os.system(HANDBRAKE % (avifile, mp4file))

            print(recdatetime)
            print("%s, %s, %s" % (year, month, day))            
            os.system(EXIFTOOL % (recdatetime, recdatetime, mp4file))
            os.system('rm %s' % mp4file+"_original")
