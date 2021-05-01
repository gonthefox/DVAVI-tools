#!/bin/sh
python dvavi2srt.py -a $1 -r recdatetime.srt -t timecode.srt
HandBrakeCLI  -i $1 \
	      --decomb -t 1 -c 1 -o $2 \
	      -f m4v -e x264 -q 20 -b 1500 -2 -T -a 1 -E faac -B 160 -6 dpl2 -D 1 \
	      -x ref=2:bframes=2:me=umh -v -s 1,2 \
	      --srt-file "recdatetime.srt","timecode.srt" \
	      --srt-lang jpn --srt-default 1 \
	      
  
