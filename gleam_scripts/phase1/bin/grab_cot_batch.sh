#!/bin/bash

# One big grab and one big cotter
# Data must be available and it'll take while for the whole thing to process

# user localisation
user=`whoami`

# host localisation
host=`hostname`
if [[ "${host:0:4}" == "epic" ]]
then
  computer="epic"
  groupq="astronomy818"
  standardq="routequeue"
  hostmem="20gb"
else
  computer="fornax"
  groupq="partner1002"
  standardq="workq"
  hostmem="70gb"
fi

rootdir=/scratch/$groupq
datadir=$rootdir/$user
codedir=$rootdir/code
queuedir=/home/$user/queue/

# Delay submission slightly so that wrapper script can reassign dependencies
LANG=en_us_8859_1
timenow=`date`
attime=`date +%H%M -d "$timenow + 2 minutes"`

# Batching -- annoying because this is what the scheduler is supposed to do for us, but it can't handle this many jobs
# Chose a batch size that makes cotter take roughly 8 hours
# Had to reduce this from 30 to 20 because disk write speed on Fornax dramatically slowed
batchsize=20

if [[ $1 ]] && [[ $2 ]]
then
 if [[ -e $1 ]]
 then

   filelist=`cat $1`
   identifier=`echo $1 | awk 'BEGIN {FS="/"} {print $NF}'`
   filelength=`cat $1 | wc -l`

   proj=$2

   if [[ ! -d $datadir/${proj} ]]
   then
    mkdir $datadir/${proj}
   fi

   cd $queuedir

   l=1 # batch number
   n=1 # obs number
   cat q_grab_header.template  | sed "s;PROJ;${proj};g" | sed "s;GROUPQ;${groupq};g" | sed "s;DATADIR;$datadir;g" > grb_${identifier}_${l}.sh
   cat q_cot_header.template  | sed "s;PROJ;${proj};g" | sed "s;HOSTMEM;${hostmem};g" | sed "s;GROUPQ;${groupq};g"  | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" > cot_${identifier}_${l}.sh
   while [[ $n -le $filelength ]]
   do
        obsnum=`sed "${n}q;d" $1`
        if [[ ! -d $datadir/${proj}/${obsnum}/${obsnum}.ms ]]
        then
          cat q_grab_body.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g"  | sed "s;DATADIR;${datadir};g" >> grb_${identifier}_${l}.sh
          cat q_cot_body.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g" | sed "s;DATADIR;${datadir};g" >> cot_${identifier}_${l}.sh
        fi
        val=`expr $n % $batchsize`
        if [[ $val -eq 0 ]]
        then
# Can't have lots of downloads at the same time
            existingjob=`qstat -u nhurleywalker | grep "grb" | tail -1 | awk '{print $1}'`
            if [[ "$existingjob" == *$computer* ]]
            then
# Other grab job doesn't necessarily have to succeed for it to be a good idea to submit the next one
                dependency="-W depend=afterany:$existingjob"
            fi
            jobnum=`qsub -a $attime $dependency grb_${identifier}_${l}.sh`
            qsub -W depend=afterok:$jobnum -a $attime cot_${identifier}_${l}.sh
            ((l+=1))
# Start a new batch
            cat q_grab_header.template  | sed "s;PROJ;${proj};g" | sed "s;GROUPQ;${groupq};g" | sed "s;DATADIR;$datadir;g" > grb_${identifier}_${l}.sh
            cat q_cot_header.template  | sed "s;PROJ;${proj};g" | sed "s;HOSTMEM;${hostmem};g" | sed "s;GROUPQ;${groupq};g"  | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" > cot_${identifier}_${l}.sh
        fi
        ((n+=1))
   done
# Submit the final batch
# Can't have lots of downloads at the same time
   existingjob=`qstat -u nhurleywalker | grep "grb" | tail -1 | awk '{print $1}'`
   if [[ "$existingjob" == *$computer* ]]
   then
# Other grab job doesn't necessarily have to succeed for it to be a good idea to submit the next one
      dependency="-W depend=afterany:$existingjob"
   fi
   jobnum=`qsub -a $attime $dependency grb_${identifier}_${l}.sh`
   qsub -W depend=afterok:$jobnum -a $attime cot_${identifier}_${l}.sh

 else
   echo "$filelist is invalid; please specify a real list of obsids."
   echo "You can use the full path, or put it in the project directory."
   exit 1
 fi
else
 echo "Give me a list of files and a project ID, e.g. grab_cot_batch.sh last_night.txt G0001 ."
 exit 1
fi

exit 0
