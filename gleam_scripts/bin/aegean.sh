#!/bin/bash

# Run Aegean with some defaults

filename=$1
bane=$2
compress=$3

background=`echo $filename | sed "s/.fits/_bkg.fits/"`
noise=`echo $filename | sed "s/.fits/_rms.fits/"`
root=`echo $filename | sed "s/.fits//"`

ncpus=20

if [[ ! -e $background ]]
then
    if [[ $bane ]]
    then
         if [[ $compress ]]
         then
             compress="--compress"
         fi
         BANE.py --cores=${ncpus} --noclobber $compress $filename
    else
         aegean.py --cores=${ncpus} --save $filename
    fi
fi

#aegean.py --seedclip=50 --telescope=mwa --island --maxsummits=5 --background=$background --noise=$noise --out=/dev/null --table=$root.vot,$root.reg $filename

if [[ ! -e ${root}_comp.vot ]]
then
    aegean.py --cores=${ncpus} --telescope=mwa --island --maxsummits=5 --background=$background --noise=$noise --out=/dev/null --table=$root.vot,$root.reg $filename
else
    echo "${root}_comp.vot already exists."
fi

exit 0

