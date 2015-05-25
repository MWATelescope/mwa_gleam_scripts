#!/usr/bin/env python

# Script to correct the flux scale by matching peak_fluxes to scaled MRC
# Hopefully will remove slow RA-dependent flux scale effects in GLEAM
# Also remove the RA, Dec shifts using MRC since it's like John's corrections but without the bugs

import os
import sys
import glob
import shutil
import numpy
from astropy.io import fits
from astropy.io.votable import parse_single_table
import re

catdir=os.environ['MWA_CODE_BASE']
MRCvot=catdir+"/MRC.vot"

#files=sorted(glob.glob("10*XX*2.0.fits")) #[::-1]
files=sorted(glob.glob("10*XX*2.1.fits")) #[::-1]
# Check all matching files and VO tables are present

for Xfits in files:
    Yfits=re.sub("XX","YY",Xfits)
    Ifits=re.sub("XX","I",Xfits)
    Ivot=re.sub(".fits","_comp.vot",Ifits)
    if not os.path.exists(Yfits):
       print "Missing "+Yfits
       sys.exit(1)
    if not os.path.exists(Ifits):
       print "Missing "+Ifits
       sys.exit(1)
    if not os.path.exists(Ivot):
       print "Missing "+Ivot
       sys.exit(1)
    Xfits_corr=re.sub(".fits","_corrected.fits",Xfits)
    Yfits_corr=re.sub(".fits","_corrected.fits",Yfits)
    Ifits_corr=re.sub(".fits","_corrected.fits",Ifits)
    if os.path.exists(Xfits_corr) and os.path.exists(Yfits_corr) and os.path.exists(Ifits_corr):
       print Xfits+" already corrected: not bothing to calculate."
       files.remove(Xfits)
   
ratio=1.0

for Xfits in files:

    ra=fits.getheader(Xfits)['CRVAL1']
    dec=fits.getheader(Xfits)['CRVAL2']
    freq=fits.getheader(Xfits)['CRVAL3']
    freq_str="%03.0f" % (freq/1e6)

# surely these filename substitutions can be made more pythonic
# inputs
    Yfits=re.sub("XX","YY",Xfits)
    Ifits=re.sub("XX","I",Xfits)
    Ivot=re.sub(".fits","_comp.vot",Ifits)
    matchvot=re.sub(".fits","_MRC.vot",Ifits)

    if not os.path.exists(matchvot):
        os.system('stilts tpipe in='+MRCvot+' cmd=\'select NULL_MFLAG\' cmd=\'addcol PA "0.0"\' cmd=\'addcol S_'+freq_str+' "S408*pow(('+str(freq)+'/408000000.0),-0.85)"\' out=temp1.vot')
        os.system('stilts tpipe in='+Ivot+' cmd=\'select local_rms<1.0\' out=temp2.vot')
        os.system('stilts tmatch2 matcher=skyellipse params=30 in1=temp1.vot in2=temp2.vot out=temp.vot values1="_RAJ2000 _DEJ2000 e_RA2000 e_DE2000 PA" values2="ra dec a b pa" ofmt=votable')
    # Exclude extended sources
        os.system('stilts tpipe in=temp.vot cmd=\'select ((int_flux/peak_flux)<2)\' cmd=\'addcol logratio "(ln(S_'+freq_str+'/peak_flux))"\' cmd=\'addcol weight "(peak_flux/local_rms)"\' cmd=\'addcol delRA "(_RAJ2000-ra)"\' cmd=\'addcol delDec "(_DEJ2000-dec)"\' omode=out ofmt=vot out=temp3.vot')
        os.system('stilts tpipe in=temp3.vot cmd=\'select abs(delRA)<1.0\' out='+matchvot)
        os.remove('temp.vot')
        os.remove('temp1.vot')
        os.remove('temp2.vot')
        os.remove('temp3.vot')

    t = parse_single_table(matchvot)
# Check the matched table actually has entries
    if t.array.shape[0]>0:
# weight is currently S/N
        ratio=numpy.exp(numpy.average(a=t.array['logratio'],weights=(t.array['weight']))) #*(distfunc)))
        stdev=numpy.exp(numpy.std(a=t.array['logratio']))
        print "Ratio of "+str(ratio)+" between "+Ifits+" and MRC."
        print "stdev= "+str(stdev)

    # Calculate ionospheric offsets
        delRA=numpy.average(a=t.array['delRA'],weights=(t.array['weight'])) #*(distfunc)))
        delDec=numpy.average(a=t.array['delDec'],weights=(t.array['weight'])) #*(distfunc)))
    #    delRAstdev=numpy.std(a=t.array['delRA'])
    #    delDecstdev=numpy.std(a=t.array['delDec'])

    # Write new fits files

        for fitsfile in Ifits,Xfits,Yfits:
            hdu_in = fits.open(fitsfile)
        # Modify to fix ionosphere
            hdr_in = hdu_in[0].header
            hdr_in['CRVAL1'] = ra + delRA
            hdr_in['CRVAL2'] = dec + delDec
        # Modify to fix flux scaling
            hdu_in[0].data=hdu_in[0].data*ratio
        # Write out
            fits_corr=re.sub(".fits","_corrected.fits",fitsfile)
            hdu_in.writeto(fits_corr,clobber=True)
    else:
        print Ifits+" had no valid matches with MRC. Moving files to unused/ ."
        obsid=Ifits.split("_")[0]
        for file in glob.glob(obsid+"*"):
            shutil.move(file,"./unused/")
