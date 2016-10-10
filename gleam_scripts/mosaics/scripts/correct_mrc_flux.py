#!/usr/bin/env python

# Script to correct the flux scale by matching int_fluxes to scaled MRC
# No longer does vector corrections, assuming that is done by the warping code

import os
import sys
import glob
import shutil
import numpy as np
from astropy.io import fits
from astropy.io.votable import parse_single_table
import re
import matplotlib as mpl
mpl.use('Agg') # So does not use display
import matplotlib.pylab as plt

from optparse import OptionParser

usage="Usage: %prog [options]\n"
parser = OptionParser(usage=usage)
parser.add_option('-i','--input',dest="input",default=None,
                  help="Input obsid to correct")
(options, args) = parser.parse_args()

if options.input and re.match("^[0-9]{10}$",options.input):
    obsid=options.input
else:
    print "Must specify input obsid"
    sys.exit(1)

def unwrap(x):
    if x>250:
        return x-360
    else:
        return x
vunwrap=np.vectorize(unwrap)

catdir=os.environ['MWA_CODE_BASE']
MRCvot=catdir+"/MWA_Tools/catalogues/MRC_extended.vot"

if not os.path.exists(MRCvot):
    print "Can't find MRC.vot in $MWA_CODE_BASE! Either it's not there or the variable wasn't set properly. Make sure you set it to the directory in which MWA_Tools resides."
    sys.exit(1)

corrfile=options.input+"_flux_corrections.txt"
f=open(corrfile,"w")

# Expects to act on an obsid with relevant Phase 2 XX, YY, I snapshots and their source-finding results.
# Would probably work on Phase 1 but hasn't been tested.
files=sorted(glob.glob(obsid+"*XX*2.?.fits")) #[::-1]

# Check all matching files and VO tables are present
docorr=[]
for Xfits in files:
    Yfits=Xfits.replace("XX","YY")
    Ifits=Xfits.replace("XX","I")
    print Ifits
    Ivot=Ifits.replace(".fits","_comp.vot")
    if not os.path.exists(Yfits):
        print "Missing "+Yfits
        sys.exit(1)
    if not os.path.exists(Ifits):
        print "Missing "+Ifits+", trying unused/"+Ifits
        Ifits="unused/"+Ifits
        if not os.path.exists(Ifits):
            print "Missing "+Ifits
            sys.exit(1)
    if not os.path.exists(Ivot):
        print "Missing "+Ivot+", trying unused/"+Ivot
        Ivot="unused/"+Ivot
        if not os.path.exists(Ivot):
            print "Missing "+Ivot
            sys.exit(1)
    Xfits_corr=re.sub(".fits","_fluxscaled.fits",Xfits)
    Yfits_corr=re.sub(".fits","_fluxscaled.fits",Yfits)
    Ifits_corr=re.sub(".fits","_fluxscaled.fits",Ifits)
    if os.path.exists(Xfits_corr) and os.path.exists(Yfits_corr) and os.path.exists(Ifits_corr):
       print Xfits+" already corrected: not bothing to calculate."
#       files.remove(Xfits)
       docorr.append(False)
    else:
       docorr.append(True)

files_to_check=zip(files,docorr)

ratio=1.0

for Xfits,corr in files_to_check:
    freq = fits.getheader(Xfits)['CRVAL3']
    freq_str = "%03.0f" % (freq/1e6)
    freq = fits.getheader(Xfits)['CRVAL3']

# surely these filename substitutions can be made more pythonic
    Ifits=re.sub("XX","I",Xfits)
    Yfits=re.sub("XX","YY",Xfits)
# inputs
    Xpb=Xfits.replace(".fits","_pb.fits")
    Ypb=Xpb.replace("XX","YY")

    Iroot=re.sub(".fits","",Ifits)
    Ivot=re.sub(".fits","_comp.vot",Ifits)

# Generate matched MRC catalogues with primary-beam-corrected images
    for image in Xpb, Ypb, Ifits:
        print image
        vot=image.replace(".fits","_comp.vot")
        matchvot=image.replace(".fits","_MRC.vot")

        if not os.path.exists(matchvot):
            print "Missing "+matchvot+", trying unused/"+matchvot
            if os.path.exists("unused/"+matchvot):
                matchvot="unused/"+matchvot
# Need to make a new matchtable
            else:
                os.system('stilts tpipe in='+MRCvot+' cmd=\'select NULL_MFLAG\' cmd=\'addcol PA "0.0"\' cmd=\'addcol S_'+freq_str+' "S408*pow(('+str(freq)+'/408000000.0),-0.85)"\' out='+image+'temp1.vot')
                os.system('stilts tpipe in='+vot+' cmd=\'select local_rms<1.0\' out='+image+'temp2.vot')
                os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+image+'temp1.vot in2='+image+'temp2.vot out='+image+'temp.vot values1="_RAJ2000 _DEJ2000 e_RA2000 e_DE2000 PA" values2="ra dec a b pa" ofmt=votable')
            # Exclude extended sources
# weight is currently S/N
                os.system('stilts tpipe in='+image+'temp.vot cmd=\'select ((int_flux/peak_flux)<2)\' cmd=\'addcol logratio "(ln(S_'+freq_str+'/int_flux))"\' cmd=\'addcol weight "(int_flux/local_rms)"\' cmd=\'addcol delRA "(_RAJ2000-ra)"\' cmd=\'addcol delDec "(_DEJ2000-dec)"\' omode=out ofmt=vot out='+image+'temp3.vot')
                os.system('stilts tpipe in='+image+'temp3.vot cmd=\'select abs(delRA)<1.0\' out='+matchvot)
                os.remove(image+'temp.vot')
                os.remove(image+'temp1.vot')
                os.remove(image+'temp2.vot')
                os.remove(image+'temp3.vot')

# Check the matched table actually has entries
    Imatchvot=Ifits.replace(".fits","_MRC.vot")
    t = parse_single_table(Imatchvot)
    if t.array.shape[0]>0:
    # Now calculate the correction factors for the I, XX and YY snapshots
        for pb in Ifits,Xpb,Ypb:
            image = pb.replace("_pb.fits",".fits")
            matchvot = pb.replace(".fits","_MRC.vot")
            t = parse_single_table(matchvot)
            ratio=np.exp(np.average(a=t.array['logratio'],weights=(t.array['weight']))) #*(distfunc)))
            stdev=np.std(a=t.array['logratio'])
            print "Ratio of "+str(ratio)+" between "+image+" and MRC."
            print "stdev= "+str(stdev)

            if corr:
                # Write new NON-primary-beam-corrected fits files
                hdu_in = fits.open(image)
            # Modify to fix flux scaling
                hdu_in[0].data *= ratio
            # Remove stupid bonus keywords, if they have been added
                try:
                    hdr_in.remove('DATAMIN')
                    hdr_in.remove('DATAMAX')
                except:
                    pass
            # Write out
                fits_corr=image.replace(".fits","_fluxscaled.fits")
                hdu_in.writeto(fits_corr,clobber=True)
                f.write("{0:s} {1:10.8f} {2:10.8f}\n".format(image,ratio,stdev))
    else:
        print pb+" had no valid matches with MRC. Moving it to unused/ ."
        shutil.move(pb,"./unused/")
f.close()
