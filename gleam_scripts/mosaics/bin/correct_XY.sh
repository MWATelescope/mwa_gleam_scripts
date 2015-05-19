#!/bin/bash

# Sourcefind, and then crossmatch the XX and YY tables for each frequency
# Fit a polynomial
# Correct the Y fits file
# Combine the X and Y together in a weighted fashion

# Source-find on the initial XX and YY mosaics

for mosaic in mosaic*-1.0.fits
do
    root=`echo $mosaic | sed "s/.fits//"`
    BANE.py --noclobber $mosaic
    if [[ ! -e ${root}_comp.vot ]]
    then
        aegean.py --island --autoload --maxsummits=5 --seedclip=8 --floodclip=5 --table=$root.vot,$root.reg --out=/dev/null --telescope=mwa $mosaic
    fi
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

fit_poly.py --rescale

# Combine the XX and YY mosaics to form a new combined mosaic, inverse weighted by their RMSs

for Xfile in mosaic*X*-1.0.fits
do
    Yfile=`echo $Xfile | sed "s/_XX_r-1.0.fits/_YY_r-1.0_resc.fits/g"`
    Xrms=`echo $Xfile | sed "s/_XX_r-1.0.fits/_XX_r-1.0_rms.fits/g"`
    Yrms=`echo $Yfile | sed "s/_resc/_resc_rms/g"`

    Xroot=`echo $Xfile | sed "s/.fits//g"`
    Yroot=`echo $Yfile | sed "s/.fits//g"`

    outimg=`echo $Xfile | sed "s/_XX_r-1.0.fits/_r-1.0_recomb.im/g"`
    outfits=`echo $Xfile | sed "s/_XX_r-1.0.fits/_r-1.0_recomb.fits/g"`

    if [[ ! -e $outfits ]]
    then

        BANE.py --noclobber $Xfile
        BANE.py --noclobber $Yfile

        echo $Yroot

        Ximg="${Xfile:0:3}X.im"
        Xrmsimg="${Xfile:0:3}rX.im"
        Xwtimg="${Xfile:0:3}wX.im"

        Yimg="${Yfile:0:3}Y.im"
        Yrmsimg="${Yfile:0:3}rY.im"
        Ywtimg="${Yfile:0:3}wY.im"

        fits op=xyin in=$Xfile out=$Ximg
        fits op=xyin in=$Yfile out=Y.temp

        regrid in=Y.temp out=$Yimg tin=$Ximg axes=1,2 tol=0
        rm -rf Y.temp

        fits op=xyin in=$Xrms out=Xrms.temp
        fits op=xyin in=$Yrms out=Yrms.temp
        
        regrid in=Yrms.temp out=$Yrmsimg tin=$Ximg axes=1,2 tol=0
        regrid in=Xrms.temp out=$Xrmsimg tin=$Ximg axes=1,2 tol=0
        rm -rf Xrms.temp
        rm -rf Yrms.temp

        maths exp="1/(<$Xrmsimg>*<$Xrmsimg>)" out=$Xwtimg
        maths exp="1/(<$Yrmsimg>*<$Yrmsimg>)" out=$Ywtimg
        maths exp="(<$Ximg>*<$Xwtimg>+<$Yimg>*<$Ywtimg>)/(<$Xwtimg>+<$Ywtimg>)" out=${outimg}

        fits op=xyout in=${outimg} out=${outfits}
        rm -rf *.im
    fi

# Do some final source-finding for onward use

    outrms=`echo $outfits | sed "s/recomb/recomb_rms/"`
    outroot=`echo $outfits | sed "s/.fits//"`

    BANE.py --noclobber $outfits
    if [[ ! -e ${outroot}_comp.vot ]]
    then
        aegean.py --island --autoload --maxsummits=5 --seedclip=8 --floodclip=5 --table=$outroot.vot,$outroot.reg --out=/dev/null --telescope=mwa $outfits
    fi

done

exit 0
