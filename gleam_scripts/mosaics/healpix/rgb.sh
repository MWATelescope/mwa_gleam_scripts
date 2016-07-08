#!/bin/bash --login
#SBATCH --account=mwasci
#SBATCH --partition=workq
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --mem=64gb
#SBATCH --output=/home/nhurleywalker/data2/nhurleywalker/G0008/Healpix/rgb.o%A
#SBATCH --error=/home/nhurleywalker/data2/nhurleywalker/G0008/Healpix/rgb.e%A

cd /home/nhurleywalker/data2/nhurleywalker/G0008/Healpix

if [[ ! -e ./rgb_map_hp.png ]]
then
   aprun -n 1 -d 1 rgb_hp.py --red red_map_hp.fits  --green green_map_hp.fits  --blue blue_map_hp.fits --transfer asinh --output rgb_map_hp.png
   convert -trim rgb_map_hp.png rgb_map_hp_trim.png
fi
if [[ ! -e ./rgb_bkg_hp.png ]]
then
   aprun -n 1 -d 1 rgb_hp.py --red red_bkg_hp.fits  --green green_bkg_hp.fits  --blue blue_bkg_hp.fits --transfer asinh --output rgb_bkg_hp.png
   convert -trim rgb_bkg_hp.png rgb_bkg_hp_trim.png
fi

#if [[ -e ./rgb_map_hp_trim.png ]]
#then
#    echo "Dividing rgb_map_hp.png into many small tiles."
#    $aprunsingle perl cutter.pl file="rgb_map_hp_trim.png" minzoom=1 maxzoom=7
#else
#    echo "rgb_map_hp_trim.png failed to create!"
#fi


exit 0

