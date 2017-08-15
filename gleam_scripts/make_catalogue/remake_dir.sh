#!/bin/bash -l

#SBATCH --account=mwaops
#SBATCH --partition=gpuq
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --mem=32gb
#SBATCH --output=/home/phancock/queue/remake_dir.sh.o%A
#SBATCH --error=/home/phancock/queue/remake_dir.sh.e%A

mydir=/home/phancock/G0008
srcdir=/scratch2/mwaops/nhurleywalker/G0008

cd ${mydir}

# delete all the links and files
find Week? -type l -exec rm {} \;
#find Week? -type f -exec rm {} \;


# copy/process all the sub bands
# link the files
dirs=`find Week[1-4]/*MHz -type d`
for d in ${dirs}; 
do 
ln -s ${srcdir}/${d}/for_upload/mosaic*.fits ${d}/.;
done;

# same again for the white images
dirs=`find Week[1-4]/white -type d`
for d in ${dirs};
do 
ln -s ${srcdir}/${d}/for_upload/mosaic*.fits ${d}/.;
done;
