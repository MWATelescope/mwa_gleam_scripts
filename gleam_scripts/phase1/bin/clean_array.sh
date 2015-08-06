#!/bin/bash

# Cool new array style cleaning
# Must already have all the measurement sets ready and calibrated
# No fancy dependencies now!!

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
# ngas storage archive destination commands are set in clean_array_casa.template

rootdir=/scratch/${groupq}
datadir=$rootdir/$user
codedir=$rootdir/code
queuedir=/home/$user/queue/

# Delay submission slightly so that wrapper script can reassign dependencies
LANG=en_us_8859_1
timenow=`date`
attime=`date +%H%M -d "$timenow + 2 minutes"`

if [[ $1 ]] && [[ $2 ]]
then

 filelist=$1
 proj=$2

 if [[ -e $filelist ]]
 then
   filelength=`cat $filelist | wc -l`
   identifier=`echo $filelist | awk 'BEGIN {FS="/"} {print $NF}'`
   cd $queuedir
   cat clean_array.template | sed "s;FILELIST;${filelist};g" | sed "s/FILELENGTH/${filelength}/g" | sed "s;PROJ;${proj};g" | sed "s;HOSTMEM;${hostmem};g" |  sed "s;CODEDIR;${codedir};g" | sed "s;GROUPQ;${groupq};g"  | sed "s;STANDARDQ;${standardq};g" | sed "s;DATADIR;$datadir;g" | sed "s;QUEUEDIR;${queuedir};g" > car_$identifier.sh
   #dependency=" -W depend=afterok:4074418.epic"
   qsub -a $attime  $dependency car_$identifier.sh
 else
   echo "$filelist is invalid; please specify a real list of obsids."
   echo "You can use the full path, or put it in the project directory."
   exit 1
 fi
else
 echo "Give me a list of files and a project ID, e.g. clean_array.sh last_night.txt G0001 ."
 echo "And optionally, some distinctive tag for the output, like mk1."
 exit 1
fi

exit 0
