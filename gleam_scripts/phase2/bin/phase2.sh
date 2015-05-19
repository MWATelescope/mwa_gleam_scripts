#!/bin/bash

# user localisation
user=`whoami`

# host localisation
if [[ "${HOST:0:4}" == "raij" ]]
then
    computer="raijin"
    groupq="fm1"
    standardq="normal"
    copyq="copyq"
    hostmem="32"
    rootdir=/short/${groupq}
    ncpus=16
    # While store04 wasn't available to the outside world
    #ngascommands="ngamsCClient_17092014 -host store02.icrar.org -port 7777 -mimeType application/octet-stream -cmd PARCHIVE -nexturl http://store04.icrar.org:7777/QARCHIVE -fileUri "
    #ngastestcommands="curl store02.icrar.org:7777/STATUS?file_id="
    ngascommands="ngamsCClient_17092014 -host store04.icrar.org -port 7777 -cmd QARCHIVE -mimeType application/octet-stream -fileUri "
    ngastestcommands="curl store04.icrar.org:7777/STATUS?file_id="
    scheduler="pbs"
    copyqsub="qsub"
elif [[ "${HOST:0:4}" == "gala" ]]
then
    computer="galaxy"
    groupq="mwaops"
    standardq="workq"
    hostmem="64"
    rootdir=/scratch/${groupq}
    ncpus=20
    ngascommands="ngamsCClient -host store04.icrar.org -port 7777 -cmd QARCHIVE -mimeType application/octet-stream -fileUri "
    ngastestcommands="curl store04.icrar.org:7777/STATUS?file_id="
    scheduler="slurm"
# Makes dependencies impossible!
#    copyqsub="sbatch -M zeus"
#    copyq="copyq"
    copyqsub="sbatch"
    copyq="gpuq"
else
    computer="fornax"
    groupq="partner676"
    standardq="workq"
    copyq="copyq"
    hostmem="70"
    rootdir=/scratch/${groupq}
    ncpus=12
    ngascommands="ngamsCClient_17092014 -host store04.icrar.org -port 7777 -cmd QARCHIVE -mimeType application/octet-stream -fileUri "
    ngastestcommands="curl store04.icrar.org:7777/STATUS?file_id="
    scheduler="pbs"
    copyqsub="qsub"
fi

datadir=$rootdir/$USER
codedir=$rootdir/code
queuedir=$HOME/queue

if [[ $scheduler == "slurm" ]]
then
    qsub="sbatch"
    depend="--dependency"
    qstat="squeue"
else
    qsub="qsub"
    depend="-W depend"
    qstat="qstat"
fi

# Chose a batch size that compromises number of jobs submitted to queue and /short space used
batchsize=10

if [[ $1 ]] && [[ $2 ]]
then

    filelist=$1
    proj=$2
    chan=$3
# Do we do all of the self-cal from scratch, download a self-calibrated ms, or use a transferred solution from another observation?
# Download a self-calibrated measurement set
    if [[ $4 == "phase2" ]]
    then
        phase="_phase2"
        solobs=""
# Do all of the self-cal from scratch
    elif [[ $4 == "self" ]]
    then
        phase=""
        solobs=""
# Use a transferred solution from another observation
    else
        phase=""
        solobs=$4
    fi

    if [[ ! -d $datadir/$proj ]]
    then
        mkdir $datadir/$proj
    fi

# If we need a solution from another observation, get that downloading
    if [[ ! -d $datadir/$proj/$solobs && ! -e $datadir/$proj/${solobs}_phase2.tar.gz ]]
    then
        dlscript="dl_${solobs}.sh"
        cat dl_icrar_${scheduler}.template  | sed "s;GROUPQ;${groupq};g" | sed "s;COPYQ;${copyq};g" | sed "s;QUEUEDIR;${queuedir};g" | sed "s;OUTPUT;${dlscript};g" > $dlscript
        cat dl_icrar_head.template  | sed "s;PROJ;${proj};g" | sed "s;DATADIR;$datadir;g" | sed "s;CHAN;${chan};g" | sed "s;PHASE;${phase};g" >> $dlscript
        cat dl_scald_body.template | sed "1,25s;SOLOBS;${solobs};g" >> dl_$solobs.sh
# Only one observation, so no worries about dependencies
        $qsub $dlscript
    fi

    if [[ -e $filelist ]]
    then
        batchident=`echo $1 | awk 'BEGIN {FS="/"} {print $NF}'`
        templist=`cat $filelist`
        length=`wc -l $filelist | awk '{print $1}'`
        lengthlimit=`expr $length - 1 `
        obslist=($templist)
        cd $queuedir
        l=1 # batch number
        n=1 # obs number
        dlscript=dl_${batchident}_${l}.sh
        cat dl_icrar_${scheduler}.template  | sed "s;GROUPQ;${groupq};g" | sed "s;COPYQ;${copyq};g" | sed "s;QUEUEDIR;${queuedir};g" | sed "s;OUTPUT;${dlscript};g" > $dlscript
        cat dl_icrar_head.template  | sed "s;PROJ;${proj};g" | sed "s;DATADIR;$datadir;g" | sed "s;CHAN;${chan};g" | sed "s;PHASE;${phase};g" >> $dlscript
        upscript=up_${batchident}_${l}.sh
        cat up_icrar_${scheduler}.template  | sed "s;PROJ;${proj};g" | sed "s;GROUPQ;${groupq};g" | sed "s;COPYQ;${copyq};g" | sed "s;DATADIR;$datadir;g" | sed "s;QUEUEDIR;${queuedir};g" | sed "s;OUTPUT;${upscript};g" > $upscript
        dl=0 # how many downloads
        img=0 # how many imaging runs

        echo "Starting batch $l"

        for (( n=0; n<$length ; n++ ))
        do
            obsnum=${obslist[$n]}
            echo "Current observation: $obsnum , n = $n"
            obsident=`echo $obsnum | awk '{print substr($1,6,5)}'`
            if [[ ! -e $datadir/$proj/$obsnum.tar.gz && ! -e $datadir/$proj/${obsnum}_phase2.tar.gz && ! -e $datadir/$proj/${obsnum}_images.tar ]]
            then 
                cat dl_icrar_body.template | sed "1,25s;OBSNUM;${obsnum};g"  >> dl_${batchident}_${l}.sh
                (( dl+=1 ))
            else
                echo "Tarballs already exist for ${obsnum}:"
                ls $datadir/$proj/${obsnum}*tar*
            fi
            if [[ ! -e $datadir/$proj/${obsnum}_images.tar ]]
            then
                cat phase2_${scheduler}.template | sed "1,25s;GROUPQ;${groupq};g" | sed "1,25s;STANDARDQ;${standardq};g" | sed "1,25s;HOSTMEM;${hostmem};g" | sed "1,25s;NCPUS;${ncpus};g" | sed "1,25s;HOMEDIR;${HOME};g" | sed "1,25s;OUTPUT;p2_${obsident};" > p2_${obsident}.sh
                cat phase2_body.template | sed "1,25s;HOSTMEM;${hostmem};g" | sed "1,25s;NCPUS;${ncpus};g" | sed "1,25s;OBSNUM;${obsnum};g" |  sed "1,25s;DATADIR;${datadir};g" | sed "1,25s;PROJ;${proj};g" | sed "1,25s;CHAN;${chan};g" | sed "1,25s;SOLOBS;${solobs};g" >> p2_${obsident}.sh
                (( img+=1 ))
            fi
            cat up_icrar_body.template | sed "s;OBSNUM;${obsnum};g" |  sed "s;DATADIR;${datadir};g"  | sed "s;PROJ;${proj};g" | sed "s;NGASCOMMANDS;$ngascommands;g" | sed "s;NGASTESTCOMMANDS;${ngastestcommands};g" >> up_${batchident}_${l}.sh
            val=`expr \( $n + 1 \) % $batchsize`
            echo "test value = $val"
# Submit if you've accumulated 10 jobs, or this is the last observation
            if [[ $val -eq 0 || $n -eq $lengthlimit ]]
            then
# Only submit download jobs if some observations actually need it
                if [[ $dl -ne 0 ]]
                then
# Can't just spam ICRAR with a million download requests -- make it dependent on the previous batch, if it exists
                    if [[ $dljobnum ]]
                    then
                        dependency="$depend=afterok:${dljobnum}"
                    else
# Make it dependent on anything that's already downloading, to avoid hammering the storage server
                        lastdljob=`$qstat -u $USER | grep dl_  | sort | tail -1 | awk '{print $1}'`
                        if [[ $lastdljob != "" ]]
                        then
                            dependency="$depend=afterany:$lastdljob"
                        fi
                    fi
                    dljobnum=`$copyqsub $dependency dl_${batchident}_${l}.sh | awk '{print $NF}'`
                    echo $dljobnum
                    dependency="$depend=afterok:${dljobnum}"
                else
                    echo "All of these observations already exist; not submitting a download job."
                fi
# loop of last 10 obsnums (or last few if this is a final batch)
                if [[ $val -eq 0 ]]
                then
                    limit=`expr $n - $batchsize`
                else
                    limit=`expr $n - $val`
                fi
     # clear upload dependencies
                updependency=""
 # Submit imaging jobs
                if [[ $img -ne 0 ]]
                then
                    for (( m=$n ; m>$limit ; m-- ))
                    do
                        echo $m
                        if [[ ${obslist[$m]} ]]
                        then
                            obsnum=${obslist[$m]}
                            echo "Submitting observation: $obsnum"
                            obsident=`echo $obsnum | awk '{print substr($1,6,5)}'`
                            jobnum=`$qsub $dependency p2_${obsident}.sh | awk '{print $NF}'`
# modified this to afterany so that uploads stop failing when a tarball doesn't exist -- we don't really care!
                            updependency=$updependency",afterany:"$jobnum
                        fi
                    done
                    updependency=${updependency#?}   # deletes first cahracter
                else
# also modified to afterany
                    updependency="afterany"
                fi
# Submit the upload script -- dependent on all self-cal jobs running correctly
                echo $updependency
                upjobnum=`$copyqsub $depend=$updependency up_${batchident}_${l}.sh | awk '{print $NF}'`
                ((l+=1))
    # Start a new batch
                if [[ $n -ne $lengthlimit ]]
                then
                    echo "Starting batch $l"
                    dlscript=dl_${batchident}_${l}.sh
                    cat dl_icrar_${scheduler}.template  | sed "s;GROUPQ;${groupq};g" | sed "s;COPYQ;${copyq};g" | sed "s;QUEUEDIR;${queuedir};g" | sed "s;OUTPUT;${dlscript};g" > $dlscript
                    cat dl_icrar_head.template  | sed "s;PROJ;${proj};g" | sed "s;DATADIR;$datadir;g" | sed "s;CHAN;${chan};g" | sed "s;PHASE;${phase};g" >> $dlscript
                    upscript=up_${batchident}_${l}.sh
                    cat up_icrar_${scheduler}.template  | sed "s;PROJ;${proj};g" | sed "s;GROUPQ;${groupq};g" | sed "s;COPYQ;${copyq};g" | sed "s;DATADIR;$datadir;g" | sed "s;QUEUEDIR;${queuedir};g" | sed "s;OUTPUT;${upscript};g" > $upscript
                    img=0
                    dl=0
                fi
            fi
        done
    else
        echo "$filelist is invalid; please specify a real list of obsids."
        echo "You can use the full path, or put it in the project directory."
        exit 1
    fi
else
    echo "Give me a list of files and a project ID, e.g. self_prev.sh /some/directory/files.txt G0001 ."
    exit 1
fi

exit 0
