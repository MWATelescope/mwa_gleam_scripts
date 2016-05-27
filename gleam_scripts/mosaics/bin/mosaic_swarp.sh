#!/bin/bash

# Create GLEAM mosaics

# user localisation
user=`whoami`

# host localisation
host=`hostname`
if [[ "${host:0:4}" == "gala" ]]
then
    computer="galaxy"
    groupq="mwasci"
    copyq="gpuq"
    scheduler="slurm"
    standardq="workq"
    hostmem="64"
    ncpus=20
    rootdir=/scratch2/$groupq
    imagerootdir=/scratch/$groupq

# Modifications for using the GPUq
#    standardq="gpuq"
#    hostmem="32"
#    ncpus=8

else
    computer="fornax"
    groupq="partner1002"
    standardq="workq"
    copyq="copyq"
    hostmem="70"
    scheduler="pbs"
    ncpus=12
    rootdir=/scratch/$groupq
    imagerootdir=/scratch/$groupq
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
imagedir=$imagerootdir/$user
queuedir=/home/$user/queue

cd $queuedir

if [[ $1 ]] && [[ $2 ]] && [[ $3 ]]
then
    checkdate=$1
    chan=$2
    proj=$3
    targetra=$4
# can only have integer decs, or the swarp script replacement will fail
    targetdec=`echo $5 | awk '{print int($1)}'`
    xsize=$6
    ysize=$7
    version=$8
    if [[ ! -z ${version+x} ]]
    then
        version=2.1
    fi

    if [[ ! -d $datadir/$proj ]]
    then
        echo "You specified project ${proj}, but that directory doesn't exist."
        exit 1
    fi
    if [[ ! -d $datadir/$proj/$checkdate ]]
    then
        mkdir $datadir/$proj/$checkdate
    fi

    regex="[1-9][0-9][0-9][0-9][0-1][0-9][0-3][0-9]"
    if [[ ! $checkdate =~ $regex ]]
    then
        echo "Date in unrecogniseable format; please use YYYYMMDD"
        exit 1
    fi

    cat drift.swarp.template | sed "s;TARGETRA;$targetra;g" | sed "s;TARGETDEC;$targetdec;g" | sed "s;XSIZE;$xsize;g" | sed "s;YSIZE;$ysize;g" > $datadir/$proj/$checkdate/drift.swarp
#    dlscript="dlm_${checkdate}_${chan}"
#    cat dl_mosaic_${scheduler}.template | sed "s;GROUPQ;${groupq};g" | sed "s;OUTPUT;${dlscript};g" | sed "s;QUEUEDIR;${queuedir};" | sed "s;COPYQ;${copyq};g" > ${dlscript}.sh
#    cat dl_mosaic_body.template | sed "s;PROJ;${proj};g" | sed "s;DATADIR;${datadir};g" | sed "s;IMAGEDIR;${imagedir};g" |  sed "s;DATE;$checkdate;g" | sed "s;CHAN;$chan;g" | sed "s;VERSION;${version};g" >> ${dlscript}.sh

    cd $datadir/$proj/$checkdate/$chan
    for subchan in subchan?
    do
        if ! ls $subchan/mos* 1>>/dev/null 2>&1
        then
            redoqa="True"
        fi
    done

 # The way this is written, the download script now needs to be a separate script, that is run and completes before this one is run. That's probably OK, because it should run on Zeus, anyway.
    if [[ $redoqa == "True" ]]
    then
        pwd
        ls subchan?/1?????????_???-???MHz_XX_r*.0_v2.?.fits > snapshots_to_process.txt
        if [[ -s snapshots_to_process.txt ]]
        then
            nsnap=`wc -l snapshots_to_process.txt | awk '{print $1}'`
            echo "Not all mosaics have been created for $datadir/$proj/$checkdate/$chan ; redoing QA for $nsnap snapshots"
            cd $queuedir
            qascript="qas_${checkdate}_${chan}"
            cat qa_snapshot_${scheduler}.template | sed "s;GROUPQ;${groupq};g" | sed "s;STANDARDQ;${standardq};g" | sed "s;HOSTMEM;${hostmem};g" | sed "s;NCPUS;$ncpus;g" |  sed "s;OUTPUT;${qascript};g" | sed "s;QUEUEDIR;${queuedir};" | sed "s;NSNAP;${nsnap};" > $qascript.sh
            cat qa_snapshot_body.template  | sed "s;PROJ;${proj};g" | sed "s;DATADIR;${datadir};g" | sed "s;DATE;$checkdate;g" | sed "s;CHAN;$chan;g" | sed "s;TARGETRA;$targetra;g" | sed "s;TARGETDEC;$targetdec;g" | sed "s;XSIZE;$xsize;g" | sed "s;YSIZE;$ysize;g"  >> ${qascript}.sh
        else
            echo "No valid snapshots in $datadir/$proj/$checkdate/$chan/subchan?"
            exit 1
        fi
    fi
    cd $queuedir
    dkscript="dkm_${checkdate}_${chan}"
    cat dk_mosaic_${scheduler}.template | sed "s;GROUPQ;${groupq};g" | sed "s;STANDARDQ;${standardq};g" | sed "s;HOSTMEM;${hostmem};g" | sed "s;NCPUS;$ncpus;g" |  sed "s;OUTPUT;${dkscript};g" | sed "s;QUEUEDIR;${queuedir};" > $dkscript.sh
    cat dk_mosaic_array.template  | sed "s;PROJ;${proj};g" | sed "s;DATADIR;${datadir};g" | sed "s;DATE;$checkdate;g" | sed "s;CHAN;$chan;g" | sed "s;TARGETRA;$targetra;g" | sed "s;TARGETDEC;$targetdec;g" | sed "s;XSIZE;$xsize;g" | sed "s;YSIZE;$ysize;g"  >> ${dkscript}.sh
    if [[ $redoqa == "True" ]]
    then
        jobnum=`$qsub $qascript.sh | awk '{print $NF}'`
        $qsub ${depend}=afterok:$jobnum $dkscript.sh
    else
        $qsub $dkscript.sh
    fi
else
    echo "Correct usage: mosaic_swarp.sh <date> <channel> <project> <ra> (h) <dec> (deg) <xsize> <ysize> (pixels)"
    echo "e.g. mosaic_swarp.sh 20141111 121 G0008 10 +18 10000 7000"
fi

exit 0
