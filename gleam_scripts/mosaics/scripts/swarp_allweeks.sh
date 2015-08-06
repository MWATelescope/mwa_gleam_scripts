#!/bin/bash
#SBATCH --account=mwaops
#SBATCH --partition=workq
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --mem=64gb
#SBATCH --output=/home/nhurleywalker/queue/swarp_allweeks.sh.o%A_%a
#SBATCH --error=/home/nhurleywalker/queue/swarp_allweeks.sh.e%A_%a
#SBATCH --array=0-3

aprun="aprun -n 1 -d 20 "
aprunsingle="aprun -n 1 -d 1 "

if [[ ! $PBS_ARRAY_INDEX ]]
then
    PBS_ARRAY_INDEX=$SLURM_ARRAY_TASK_ID
fi

# Giant RGB mosaics
colors="red green blue white"
arr=($colors)
color=${arr[$PBS_ARRAY_INDEX]}

datadir=/scratch2/mwaops/nhurleywalker
proj=G0008

weeks="Week1 Week2 Week3 Week4"
projections="CAR SCP ARC MOL"

cd $datadir/$proj/allweeks

for week in $weeks
do
    if [[ -e ../${week}/${color}/${week}_${color}_lownoise.fits ]]
    then
        ln -s ../${week}/${color}/${week}_${color}_lownoise.fits
    fi
        
    if [[ ! -e ${week}_${color}_lownoise_rms.fits ]]
    then
        SR6.py -x -o ./${week}_${color}_lownoise_rms.fits ../${week}/${color}/${week}_${color}_lownoise_rms.fits 
    fi
    if [[ -e ${week}_${color}_lownoise_rms.fits ]]
    then
        pyhead.py -u BSCALE 0.000001 ${week}_${color}_lownoise_rms.fits
    fi
done
# Rescale RMS

for projection in $projections
do
    if [[ ! -e ${color}_${projection}.fits ]]
    then
        $aprun swarp -c allweeks_${projection}.swarp Week?_${color}_lownoise.fits -IMAGEOUT_NAME ${color}_${projection}.fits
        $aprun fits_trim.py ${color}_${projection}.fits temp.fits
        mv temp.fits ${color}_${projection}.fits
    fi
done

for week in $weeks
do
# De-rescale RMS
    if [[ -e ${week}_${color}_lownoise_rms.fits ]]
    then
        pyhead.py -u BSCALE 1.0 ${week}_${color}_lownoise_rms.fits
    fi
done
