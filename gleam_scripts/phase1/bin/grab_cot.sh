#!/bin/bash

# Downloads data via NGAS
# Then submits cotter job
# Data must be available on the archive!

# Edit / add to these options for your supercomputer
if [[ "${HOST:0:4}" == "gala" ]]
then
    computer="galaxy"
    group="mwasci"
    standardq="workq"
    hostmem="64" #GB
    qsub="sbatch"
    copyqsub="sbatch -M zeus"
    copyq="copyq"
    scheduler="slurm"
    scratch=/scratch2
else
    computer="epic"
    group="astronomy818"
    standardq="routequeue"
    hostmem="20gb"
    scheduler="pbs"
    scratch=/scratch
fi

rootdir=$scratch/$group
datadir=$rootdir/$USER
codedir=$rootdir/code
queuedir=$HOME/queue

if [[ $1 ]] && [[ $2 ]]
then
    obsnum=$1
    proj=$2
    if [[ ! -d $datadir/${proj} ]]
    then
        mkdir $datadir/${proj}
    fi
    cd $queuedir
    if [[ ! -d $datadir/${proj}/${obsnum}/${obsnum}.ms ]]
    then
        cat grab_${scheduler}.template  | sed "s;PROJ;${proj};g" | sed "s;COPYQ;${copyq};g" | sed "s;DATADIR;$datadir;g" | sed "s;OUTPUT;grb_${obsnum};" | sed "s;QUEUEDIR;${queuedir};" | sed "s;GROUP;${group};" > grb_${obsnum}.sh
        cat cot_${scheduler}.template  | sed "s;PROJ;${proj};g" | sed "s;HOSTMEM;${hostmem};g" | sed "s;GROUP;${group};g"  | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" | sed "s;OUTPUT;cot_${obsnum};" | sed "s;QUEUEDIR;${queuedir};" > cot_${obsnum}.sh
        cat grab_body.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g"  | sed "s;DATADIR;${datadir};g" >> grb_${obsnum}.sh
        cat cot_body.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g" | sed "s;DATADIR;${datadir};g" >> cot_${obsnum}.sh
    fi
    echo "$qsub -M galaxy ${queuedir}/cot_${obsnum}.sh" >> grb_${obsnum}.sh
    $copyqsub grb_${obsnum}.sh
else
    echo "Give me an observation number and a project ID, e.g. grab_cot.sh 1012345678 G0001 ."
    exit 1
fi

exit 0
