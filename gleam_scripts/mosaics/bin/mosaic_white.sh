#!/bin/bash

# Create GLEAM mosaics

# user localisation
user=`whoami`

# host localisation
host=`hostname`
if [[ "${host:0:4}" == "gala" ]]
then
    computer="galaxy"
    groupq="mwaops"
    standardq="workq"
    copyq="gpuq"
    hostmem="64"
    scheduler="slurm"
    ncpus=20
    rootdir=/scratch2/$groupq
else
    computer="fornax"
    groupq="partner1002"
    standardq="workq"
    copyq="copyq"
    hostmem="70"
    scheduler="pbs"
    ncpus=12
    rootdir=/scratch/$groupq
fi

if [[ $scheduler == "slurm" ]]
then
   qsub="sbatch"
   depend="--dependency"
else
   qsub="qsub"
   depend="-W depend"
fi

datadir=$rootdir/$user
queuedir=/home/$user/queue
# We're getting so specific here that I doubt this is going to change!
proj=G0008

cd $queuedir

if [[ $1 ]] # && [[ $2 ]] # && [[ $3 ]]
then
    week=$1

    swarpscript=white_${week}.sh
    cat white_mosaic_${scheduler}.template | sed "s;GROUPQ;${groupq};g" | sed "s;STANDARDQ;${standardq};g" | sed "s;HOSTMEM;${hostmem};g" | sed "s;NCPUS;$ncpus;g" |  sed "s;OUTPUT;${swarpscript};g" | sed "s;QUEUEDIR;${queuedir};" > $swarpscript
    cat white_mosaic_body.template  | sed "s;PROJ;${proj};g" | sed "s;DATADIR;${datadir};g" | sed "s;WEEK;${week};g" >> $swarpscript
    $qsub $swarpscript
else
    echo "Correct usage: mosaic_white.sh <week>"
    echo "e.g. mosaic_white.sh Week2"
fi

exit 0
