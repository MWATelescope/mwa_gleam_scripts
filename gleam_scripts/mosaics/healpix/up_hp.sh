#!/bin/bash -l

# Send Healpix maps to Danny

#SBATCH --account=mwasci
#SBATCH --partition=copyq
#SBATCH --time=10:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --output=/home/nhurleywalker/queue/up_hp.sh.o%j
#SBATCH --error=/home/nhurleywalker/queue/up_hp.sh.e%j
#SBATCH --export=NONE

cd /scratch2/mwasci/nhurleywalker/G0008/Healpix

scp blue_map_hp.fits nhw@enterprise.sese.asu.edu:/data6/HERA/
scp green_map_hp.fits nhw@enterprise.sese.asu.edu:/data6/HERA/
scp white_map_hp.fits nhw@enterprise.sese.asu.edu:/data6/HERA/
scp red_map_hp.fits nhw@enterprise.sese.asu.edu:/data6/HERA/
