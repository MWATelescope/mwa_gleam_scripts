#!/bin/bash -l
#SBATCH --account=mwasci
#SBATCH --partition=gpuq
#SBATCH --time=01:30:00
#SBATCH --nodes=1
#SBATCH --mem=32gb
#SBATCH --output=/home/phancock/queue/prior_fit_WEEK.sh.o%A_%a
#SBATCH --error=/home/phancock/queue/prior_fit_WEEK.sh.e%A_%a
#SBATCH --array=1-20

function doit {
    echo "$@"
    aprun -n 1 -d 8 $@
}

# Get the new version of Aegean
export PATH=/group/mwaops/phancock/code/Aegean:$PATH
export PYTHONPATH=/group/mwaops/phancock/code/Aegean:$PYTHONPATH

datadir=/scratch2/mwaops/phancock
proj=G0008
week=WEEK

# Convert SLURM id to PBS id
if [[ ! $PBS_ARRAY_INDEX ]]
then
    PBS_ARRAY_INDEX=$SLURM_ARRAY_TASK_ID
fi

cd $datadir/$proj/$week

# Include RGBW images by changing *z/ to */ (and change array=1-20 to array=1-24, above)
freq=`ls -d *z/ | sed "s;/;;g" | head -${PBS_ARRAY_INDEX} | tail -1`

cd $freq


inputimage="mosaic_${week}_${freq}.fits"
# Find the right input file
if [[ ! -e ${inputimage} ]]
then
    exit
fi


# Priorized source finding from the white image
refcat="../white/mosaic_${week}_170-231MHz_psf_QC_comp.fits"
refpsf="../white/mosaic_${week}_170-231MHz_psf.fits"
outcat="mosaic_${week}_${freq}_priorized"
if [[ ! -e "${outcat}_comp.fits" ]]
then
    echo "Making ${outcat}.fits"
    doit aegean.py --telescope=mwa --island --maxsummits=25 --autoload --out=/dev/null \
                     --table=${outcat}.vot,${outcat}.reg,${outcat}.fits ${inputimage} --priorized 1 \
                     --input=${refcat} --catpsf=${refpsf}
else
    echo "${outcat}_comp.fits already exists"
fi
