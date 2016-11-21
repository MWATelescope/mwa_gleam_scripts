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
    if [[ ! -e  ./${week}_${color}_map_hp.fits ]]
    then
        echo "Creating healpix map ${week}_${color}_map_hp.fits."
        $aprunsingle fits2hp.py -f ../$week/$color/${week}_${color}_lownoise.fits --unseen 0.0 -o ./${week}_${color}_map_hp.fits -n 4096 
    fi
    if [[ ! -e  ./${week}_${color}_rms_hp.fits ]]
    then
        echo "Creating healpix rms map ${week}_${color}_rms_hp.fits."
        $aprunsingle fits2hp.py -f ../$week/$color/${week}_${color}_lownoise_rms.fits --unseen 1.67E30 -o ./${week}_${color}_rms_hp.fits -n 4096
    fi
done

if [[ ! -e ./${color}_map_hp.fits ]]
then
    echo "Creating combined healpix map ${color}_map_hp.fits."
    $aprunsingle combine_hp.py -f "*_${color}_map_hp.fits" -r "*_${color}_rms_hp.fits" -o ${color}_map_hp.fits
fi

if [[ ! -e ./${color}_map_hp.png ]]
then
    echo "Creating image ${color}_map_hp.png."
    $aprunsingle plot_hp.py -f ./${color}_map_hp.fits -o ${color}_map_hp.png -c ${cmap}
fi

if [[ -e ./${color}_map_hp.png ]]
then
    echo "Dividing ${color}_map_hp.png into many small tiles."
    $aprunsingle perl cutter.pl file="${color}_map_hp.png" minzoom=1 maxzoom=7
else
    echo "${color}_map_hp.png failed to create!"
fi

if [[ ! -e ./${color}_map_car.png ]]
then
   echo "Reprojecting ${color}_map_hp.fits to a Cartesian fits file."
   $aprunsingle hp2cart.py --input ${color}_map_hp.fits --xpix 21440 --output ${color}_map_car.fits
fi

exit 0

