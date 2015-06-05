#!/bin/bash

for week in Week3
do
    cd $week 
    for freq in *z 
    do
        cd $freq 
        scaling=`grep "$week $freq" ../../scaling_to_use.txt | awk '{print $3}'`
        rescale_zerofits.py --mosaic=${week}_${freq}.fits --zerofits=${week}_${freq}_${scaling}_zero.fits 
        cd ../ 
    done 
    cd ../ 
done
