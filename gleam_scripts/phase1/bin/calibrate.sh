#!/bin/bash

# Calibrate some new data

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

rootdir=/scratch/${groupq}
datadir=$rootdir/$user
codedir=$rootdir/code
queuedir=/home/$user/queue/


if [[ $1 ]] && [[ $2 ]]
then

 obsnum=$1
 proj=$2

 cd $queuedir

 cat cal.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g" | sed "s;CODEDIR;${codedir};g" | sed "s;GROUPQ;${groupq};g"  | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" > cal_${obsnum:5:5}.sh

 if [[ ! -d  $datadir/${proj}/$obsnum/$obsnum.cal ]]
 then
 
  existingjob=`qstat -u nhurleywalker | grep cot_${obsnum:5:5} | awk '{print $1}'`
  if [[ "$existingjob" == *$computer* ]]
  then
   echo "I see it's in the queue."
   dependency="-W depend=afterok:$existingjob"
  else
   echo "No dependency detected."
  fi
  #dependency="-W depend=afterany:4075829.epic"
  jobnum=`qsub $dependency cal_${obsnum:5:5}.sh`

  cat q_send_data.template | sed "s;OBSNUM;${obsnum};g" | sed "s;PROJ;${proj};g" | sed "s;DATADIR;$datadir;g" | sed "s;GROUPQ;${groupq};g"  > snd_${obsnum:5:5}.sh
  qsub -W depend=afterok:$jobnum snd_${obsnum:5:5}.sh
 else
  echo "Already calibrated; please delete the caltable and try again."
  exit 1
 fi

else
 echo "Give me an obsnum and project, e.g. calibrate.sh 1012345678 C001"
 exit 1
fi

exit 0
