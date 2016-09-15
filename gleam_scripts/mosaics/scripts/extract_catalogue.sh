#!/bin/bash

# Filter each of the psf-corrected white catalogues and then join them together to produce one enormous catalogue
# Eventually this could be adapted to run on the priorised fit catalogues

# RA_Dec_ranges.txt has a copy of the footprints from the Google Doc.

decmins="0 -30 -90"

# Depends on whether we want to use the lownoise catalogue or the noweight catalogue
# This will be replaced with the priorised fit catalogue anyway
weight="noweight"

for week in ../Week?
do
    week=`basename $week`
    ln -s ../$week/white/${week}_white_${weight}_psfcorr_comp.vot
    for decmin in $decmins
    do
        echo "$week, min Dec $decmin"
 # Week1 has nothing to contribute to the highest Dec, thanks to the ionosphere
        if [[ $decmin == "0" && $week == "Week1" ]]
        then
            echo "Skipping Week 1's crappy ionosphere..."
        else
            decmax=`grep "$week $decmin" RA_Dec_ranges.txt | awk '{print $3}'`
            ramin=`grep "$week $decmin" RA_Dec_ranges.txt | awk '{print $4}'`
            ramax=`grep "$week $decmin" RA_Dec_ranges.txt | awk '{print $5}'`
            QC_filter.py --input=${week}_white_${weight}_psfcorr_comp.vot --output=${week}_${weight}_${decmin}.vot --minRA=$ramin --maxRA=$ramax --minDec=$decmin --maxDec=$decmax
            stiltsin="$stiltsin in=${week}_${weight}_${decmin}.vot"
        fi
    done
done
stilts tcat $stiltsin out=complete.vot
