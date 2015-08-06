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

week=$1

if [[ $week == "Week1" ]]
then
    ra=23
elif [[ $week == "Week2" ]]
then
    ra=04
elif [[ $week == "Week3" ]]
then
    ra=11
elif [[ $week == "Week4" ]]
then
    ra=17
else
    echo "Week not given correctly: specify like 'WeekN', where N=1-4"
    echo "e.g. mosaic_week.sh Week2"
    exit 1
fi

if [[ ! -d $datadir/$proj/$week ]]
then
    mkdir $datadir/$proj/$week
fi
if [[ ! -e $datadir/$proj/$week/weight.swarp ]]
then
    cat weight.swarp.template | sed "s/TARGETRA/$ra/" > $datadir/$proj/$week/weight.swarp
fi

swarpscript=swarp_${week}.sh
cat week_mosaic_${scheduler}.template | sed "s;GROUPQ;${groupq};g" | sed "s;STANDARDQ;${standardq};g" | sed "s;HOSTMEM;${hostmem};g" | sed "s;NCPUS;$ncpus;g" |  sed "s;OUTPUT;${swarpscript};g" | sed "s;QUEUEDIR;${queuedir};" > $swarpscript
cat week_mosaic_array.template  | sed "1,40s;PROJ;${proj};g" | sed "s;DATADIR;${datadir};g" | sed "s;WEEK;${week};g" >> $swarpscript
$qsub $swarpscript

exit 0
