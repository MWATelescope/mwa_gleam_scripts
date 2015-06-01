#!/bin/bash -l

# Sourcefind, and then crossmatch the XX and YY tables for each frequency
# Fit a polynomial
# Correct the Y fits file
# Combine the X and Y together in a weighted fashion

# Source-find on the initial XX and YY mosaics
aprun="aprun -n 1 -d 20 "

for mosaic in mosaic*-1.0.fits
do
    $aprun aegean.sh $mosaic bane
done

# Crossmatch the resulting XX and YY tables

for Xvot in *XX*_comp.vot
do
    Yvot=`echo $Xvot | sed "s/X/Y/g"`
    out=`echo $Xvot | sed "s/XX/XY/g"`
    if [[ ! -e $out ]]
    then
    stilts tmatch2 matcher=sky params=10 \
                    in1=./$Xvot  values1="ra dec" suffix1="_X" \
                    in2=./$Yvot  values2="ra dec" suffix2="_Y" \
                    out=${out} ofmt=votable \
                    fixcols=all #2>&1 | tee new.log
    fi
done

# Fit a polynomial to the resulting cross-matched catalogue, and correct YY to XX

$aprun fit_poly.py --rescale

# Combine the XX and YY mosaics to form a new combined mosaic, inverse weighted by their RMSs

Xfile=`ls mosaic*X*-1.0.fits`
Yfile=`echo $Xfile | sed "s/_XX_r-1.0.fits/_YY_r-1.0_resc.fits/g"`
outfile=`echo $Xfile | sed "s/_XX_r-1.0.fits/_r-1.0_recomb.fits/g"`

if [[ ! -e $outfile ]]
then
    $aprun aegean.sh $Xfile bane
    $aprun aegean.sh $Yfile bane
    $aprun swarp -c ../../drift.swarp $Xfile $Yfile -IMAGEOUT_NAME $outfile -WEIGHTOUT_NAME temp.weight.fits -PROJECTION_TYPE ZEA
    $aprun fits_trim.py $outfile tempdrift.fits
    mv tempdrift.fits $outfile
    rm temp.weight.fits

# Do some final source-finding for onward use
    $aprun aegean.sh $outfile bane
fi

exit 0
