#!/bin/bash

if [[ $1 ]]
then
   wget -O $1 http://store02.icrar.org:7777/RETRIEVE?file_id=$1
else
   echo "Usage: trigdown.sh 1012345678_rest_of_file_description.fits"
   exit 1
fi

exit 0

