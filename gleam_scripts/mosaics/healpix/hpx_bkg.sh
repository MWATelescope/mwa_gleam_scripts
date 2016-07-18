#!/bin/bash --login
#SBATCH --account=mwasci
#SBATCH --partition=workq
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --mem=64gb
#SBATCH --output=/home/nhurleywalker/data2/nhurleywalker/G0008/Healpix/hpx.o%A_%a
#SBATCH --error=/home/nhurleywalker/data2/nhurleywalker/G0008/Healpix/hpx.e%A_%a
#SBATCH --array=0-3

if [[ ! $PBS_ARRAY_INDEX ]]
then
    PBS_ARRAY_INDEX=$SLURM_ARRAY_TASK_ID
fi

# Giant RGB mosaics
colors="red green blue white"
arr=($colors)
color=${arr[$PBS_ARRAY_INDEX]}
if [[ "$color" == "red" ]]
then
    cmap="Reds_r"
elif [[ "$color" == "green" ]]
then
    cmap="Greens_r"
elif [[ "$color" == "blue" ]]
then
    cmap="Blues_r"
elif [[ "$color" == "white" ]]
then
    cmap="Greys_r"
fi

aprun="aprun -n 1 -d 20 "
aprunsingle="aprun -n 1 -d 1 "

weeks="Week1 Week2 Week3 Week4"
cd /home/nhurleywalker/data2/nhurleywalker/G0008/Healpix

for week in $weeks
do
    if [[ ! -e  ./${week}_${color}_bkg_hp1.fits ]]
    then
        echo "Creating healpix bkg ${week}_${color}_bkg_hp1.fits."
        $aprunsingle fits2hp.py -f ../$week/$color/${week}_${color}_lownoise_bkg.fits --unseen 0.0 -o ./${week}_${color}_bkg_hp1.fits -n 1024
    fi
    if [[ ! -e  ./${week}_${color}_rms_hp1.fits ]]
    then
        echo "Creating healpix rms map ${week}_${color}_rms_hp1.fits."
        $aprunsingle fits2hp.py -f ../$week/$color/${week}_${color}_lownoise_rms.fits --unseen 1.67E30 -o ./${week}_${color}_rms_hp1.fits -n 1024
    fi
done

if [[ ! -e ./${color}_bkg_hp1.fits ]]
then
    echo "Creating combined healpix bkg ${color}_bkg_hp1.fits."
    $aprunsingle combine_hp.py -f "*_${color}_bkg_hp1.fits" -r "*_${color}_rms_hp1.fits" -o ${color}_bkg_hp.fits
fi

if [[ ! -e ./${color}_bkg_hp.png ]]
then
    echo "Creating image ${color}_bkg_hp.png."
    $aprunsingle plot_hp.py -f ./${color}_bkg_hp.fits -o ${color}_bkg_hp.png -c ${cmap}
fi

if [[ ! -e ./${color}_bkg_car.png ]]
then
   echo "Reprojecting ${color}_bkg_hp1.fits to a Cartesian fits file."
   $aprunsingle hp2cart.py --input ${color}_bkg_hp.fits --xpix 2440 --output ${color}_bkg_car.fits
fi

exit 0

