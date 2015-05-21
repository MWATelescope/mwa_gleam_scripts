#!/bin/bash

# Calibrate data in bulk

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

if [[ $1 ]] && [[ $2 ]]
then

 filelist=`cat $1`
 identifier=`echo $1 | awk 'BEGIN {FS="/"} {print $NF}'`
 filelength=`cat $1 | wc -l`
 proj=$2

 if [[ $3 ]]
 then
    calnum=$3

# Check if the calibration table exists
    if [[ ! -d  $datadir/${proj}/$calnum/$calnum.cal ]]
    then
# Check if the calibration is in the queue
        existingjob=`qstat -u nhurleywalker | grep cal_${calnum:5:5} | awk '{print $1}'`
        if [[ "$existingjob" == *$computer* ]]
        then
           echo "I see you're still creating the calibration table."
           dependency="-W depend=afterok:$existingjob"
        fi
    fi 
 fi
 cd $queuedir

 cat applycal_batch.template | sed "s;PROJ;${proj};g" | sed "s;DATADIR;${datadir};g" | sed "s;STANDARDQ;${standardq};g" | sed "s;GROUPQ;${groupq};g" | sed "s;IDENT;${identifier};g" > aply_${identifier}.sh

 echo "" > ${datadir}/${proj}/applycal_${identifier}.py
 for obsnum in $filelist
 do
   if [[ ! $3 ]]
   then
     calnum=${obsnum}
   else
     calnum=$3
   fi
   if [[ -d ${datadir}/${proj}/${calnum}/${calnum}_clip.cal ]]
   then
       echo "applycal(vis='${obsnum}/${obsnum}.ms',gaintable='${calnum}/${calnum}_clip.cal')" >> ${datadir}/${proj}/applycal_${identifier}.py
   elif [[ -d ${datadir}/${proj}/${calnum}/${calnum}.cal ]]
   then
       echo "applycal(vis='${obsnum}/${obsnum}.ms',gaintable='${calnum}/${calnum}.cal')" >> ${datadir}/${proj}/applycal_${identifier}.py
   else
       echo "calibrator ${calnum} doesn't exist!"
       exit 1
   fi
 done
 qsub -a $attime $dependency aply_${identifier}.sh

else
 echo "Give me a list of obsnums and project, and optionally, another obsnum from which to calibrate."
 echo "e.g. applycal_batch.sh Dec-10.txt C001 1012387654"
 exit 1
fi

exit 0
