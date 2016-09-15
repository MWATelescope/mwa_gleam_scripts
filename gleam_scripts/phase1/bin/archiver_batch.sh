#!/bin/bash

# Archive calibrated measurement sets and interim image files

# user localisation
user=`whoami`

# host localisation
host=`hostname`

if [[ "${host:0:4}" == "epic" ]]
then
     computer="epic"
     groupq="astronomy818"
     standardq="routequeue"
     hostmem="10gb"
     ngascommands="ngamsCClient -host store04.icrar.org -port 7777 -cmd QARCHIVE -mimeType application/octet-stream -fileUri "
 else
     computer="fornax"
     groupq="partner1002"
     standardq="workq"
     hostmem="30gb"
     ngascommands="ngamsCClient -host store04.icrar.org -port 7777 -cmd QARCHIVE -mimeType application/octet-stream -fileUri "
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
# Chose a batch size that makes the archiving take roughly 8 hours
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
    echo "$datadir/${proj} doesn't exist!"
    exit 1
   fi

   cd $queuedir

   l=1 # batch number
   n=1 # obs number
   cat q_archive_head.template  | sed "s;PROJ;${proj};g" | sed "s;GROUPQ;${groupq};g" | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" | sed "s;HOSTMEM;${hostmem};g"  > arc_${identifier}_${l}.sh
   while [[ $n -le $filelength ]]
   do
        obsnum=`sed "${n}q;d" $1`
# Assumes that measurement set will exist by the time the archiver starts running
        cat q_archive_body.template  | sed "s;PROJ;${proj};g" | sed "s;DATADIR;$datadir;g" | sed "s;OBSNUM;$obsnum;g" | sed "s;NGASCOMMANDS;$ngascommands;g" >> arc_${identifier}_${l}.sh
        val=`expr $n % $batchsize`
        if [[ $val -eq 0 ]]
        then
# Can't have lots of archiving at the same time
            existingjob=`qstat -u nhurleywalker | grep "arc" | tail -1 | awk '{print $1}'`
            if [[ "$existingjob" == *$computer* ]]
            then
# Other archiving job doesn't necessarily have to succeed for it to be a good idea to submit the next one
                dependency="-W depend=afterany:$existingjob"
            fi
            qsub -a $attime $dependency arc_${identifier}_${l}.sh
            ((l+=1))
# Start a new batch
            cat q_archive_head.template  | sed "s;PROJ;${proj};g" | sed "s;GROUPQ;${groupq};g" | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" | sed "s;HOSTMEM;${hostmem};g" > arc_${identifier}_${l}.sh
        fi
        ((n+=1))
   done
# Submit the final batch
# Can't have lots of archiving at the same time
   existingjob=`qstat -u nhurleywalker | grep "arc" | tail -1 | awk '{print $1}'`
   if [[ "$existingjob" == *$computer* ]]
   then
# Other archiving job doesn't necessarily have to succeed for it to be a good idea to submit the next one
      dependency="-W depend=afterany:$existingjob"
   fi
   qsub -a $attime $dependency arc_${identifier}_${l}.sh
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
