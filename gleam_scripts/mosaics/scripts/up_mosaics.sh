#!/bin/bash -l

# Upload the mosaics

#SBATCH --account=mwaops
#SBATCH --partition=gpuq
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --mem=100mb

cd /scratch2/mwaops/nhurleywalker/G0008

dir2=""

for week in Week?
do
    cd $week
    dirlist=`ls -d */`
    for dir in $dirlist
    do
        dir=`echo $dir | sed "s;/;;g"`
        cd $dir
        if [[ $dir == "red" ]]
        then
            freqrange="072-103MHz"
        elif [[ $dir == "green" ]]
        then
            freqrange="103-134MHz"
        elif [[ $dir == "blue" ]]
        then
            freqrange="139-170MHz"
        elif [[ $dir == "white" ]]
        then
            freqrange="170-231MHz"
        else
            freqrange=$dir
        fi
        
        mkdir for_upload
        cd for_upload
        
        if [[ -e ../${week}_${dir}_rescaled.fits ]]
        then
            ln -s ../${week}_${dir}_rescaled.fits ./mosaic_${week}_${freqrange}.fits
            ln -s ../${week}_${dir}_resid_excl_triple.fits ./mosaic_${week}_${freqrange}_psf.fits
            ln -s ../${week}_${dir}_rescaled_bkg.fits ./mosaic_${week}_${freqrange}_bkg.fits
            ln -s ../${week}_${dir}_rescaled_rms.fits ./mosaic_${week}_${freqrange}_rms.fits
        elif [[ -e ../${week}_${dir}_noweight.fits ]]
        then
            ln -s ../${week}_${dir}_noweight.fits ./mosaic_${week}_${freqrange}.fits
            ln -s ../${week}_${dir}_noweight_resid_excl_triple.fits ./mosaic_${week}_${freqrange}_psf.fits
            ln -s ../${week}_${dir}_noweight_bkg.fits ./mosaic_${week}_${freqrange}_bkg.fits
            ln -s ../${week}_${dir}_noweight_rms.fits ./mosaic_${week}_${freqrange}_rms.fits
        fi
# have already uploaded this one
        for mosaic in mosaic*
        do
            ngamsCClient -host store04.icrar.org -port 7777 -cmd QARCHIVE -mimeType application/octet-stream -fileUri  $mosaic
            curl store04.icrar.org:7777/STATUS?file_id=$mosaic > test.txt
            localfilesize=`ls -Hl $mosaic | awk '{print $5}'`
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
        done
        cd ../
        cd ../
    done
    cd ../
done

