#!/bin/bash -l

# Upload the files

#SBATCH -p copyq
#SBATCH --account=mwasci
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1

cd /scratch2/mwasci/nhurleywalker/G0008/Healpix

for file in *.fits *.png
do
   if [[ -s $file ]]
    then
        ngamsCClient -host store06.icrar.org -port 7777 -cmd QARCHIVE -mimeType application/octet-stream -fileUri  $file
        curl store04.icrar.org:7777/STATUS?file_id=$file > test.txt
        localfilesize=`ls -Hl $file | awk '{print $5}'`
        remotefilesize=`grep FileSize test.txt | awk 'BEGIN {FS="FileSize=\""} {print $2}' | awk 'BEGIN {FS="\""} {print $1}'`
        creation=`grep CreationDate test.txt | awk 'BEGIN {FS="CreationDate=\""} {print $2}' | awk 'BEGIN {FS="\""} {print $1}' | awk 'BEGIN {FS="T"} {print $1}'`
        # ICRAR storage is in UTC
        today=`TZ=GMT0 date +%Y-%m-%d`
        if [[ $localfilesize -eq $remotefilesize && $creation == $today ]]
        then
            echo "NGAS upload successful!"
            rm test.txt
        else
            echo "File upload to NGAS failed!"
            exit 1
        fi
    else
        echo "$file was zero-size."
    fi
done
