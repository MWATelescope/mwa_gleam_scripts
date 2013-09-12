#!/bin/csh -f

rm /nfs/blank/h4215/aaronew/MWA_Tools/eorlive/*.png
source /nfs/blank/h4215/aaronew/.cshrc
cd /nfs/blank/h4215/aaronew/MWA_Tools/eorlive
./generate_beam_image.py
