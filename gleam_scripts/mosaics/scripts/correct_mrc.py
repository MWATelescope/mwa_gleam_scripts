#!/usr/bin/env python

# Script to correct the flux scale by matching int_fluxes to scaled MRC
# Hopefully will remove slow RA-dependent flux scale effects in GLEAM
# Also remove the RA, Dec shifts using MRC
# And plot nice vectors, if desired

import os
import sys
import glob
import shutil
import numpy
from astropy.io import fits
from astropy.io.votable import parse_single_table
import re
import matplotlib as mpl
mpl.use('Agg') # So does not use display
import matplotlib.pylab as plt

from optparse import OptionParser

usage="Usage: %prog [options]\n"
parser = OptionParser(usage=usage)
parser.add_option('--plot',action="store_true",dest="make_plots",default=False,
                  help="Make vector plots? (off by default)")
parser.add_option('--dec',dest="dec",default=None,type="float",
                  help="Declination of the observations to set plotting ranges. (default is to try to get from the date)")
parser.add_option('--date',dest="date",default=None,type="string",
                  help="Date of observations in YYYYMMDD format? (default is try to read from directory name) Not used if --dec is specified.")
(options, args) = parser.parse_args()

def unwrap(x):
    if x>250:
        return x-360
    else:
        return x
vunwrap=numpy.vectorize(unwrap)

catdir=os.environ['MWA_CODE_BASE']
MRCvot=catdir+"/MWA_Tools/catalogues/MRC.vot"

if not os.path.exists(MRCvot):
    print "Can't find MRC.vot in $MWA_CODE_BASE! Either it's not there or the variable wasn't set properly. Make sure you set it to the directory in which MWA_Tools resides."
    sys.exit(1)

if options.dec:
    plotdec=options.dec
else:
    if options.date:
        date=options.date
    else:
    # Expecting to be in a directory named with the date in format YYYYMMDD
        date=re.search("201[0-9]{5}",os.getcwd()).group()
        chan=re.search("\/[0-9]{2,3}\/",os.getcwd()).group().replace("/","")
        if date=="20130817" or date=="20131111" or date=="20140308" or date=="20140615" :
            plotdec=18.6
        elif date=="20130808" or date=="20131107" or date=="20140306" or date=="20140611":
            plotdec=1.6
        elif date=="20130822" or date=="20131105" or date=="20140304" or date=="20140613" or date=="20140616":
            plotdec=-13
        elif date=="20130810" or date=="20131125" or date=="20140303" or date=="20140609":
            plotdec=-27
        elif date=="20130825" or date=="20131106" or date=="20140316" or date=="20140610":
            plotdec=-40
        elif date=="20130809" or date=="20131108" or date=="20140317" or date=="20140612" or date=="20140618":
            plotdec=-55
        elif date=="20130818" or date=="20131112" or date=="20140309" or date=="20140614":
            plotdec=-72
        else:
            print "Defaulting to zenith in the absence of a known plotdeclination."
            plotdec=-27

corrfile=date+"_"+"Dec"+str(plotdec)+"_"+chan+"_corrections.txt"
f=open(corrfile,"w")

# Expects to act on a directory full of Phase 2 XX, YY, I snapshots and their source-finding results.
# Would probably work on Phase 1 but hasn't been tested.
files=sorted(glob.glob("10*XX*2.?.fits")) #[::-1]

if options.make_plots:
    # Assume that the first file is at the right frequency!
    freq=fits.getheader(files[0])['CRVAL3']

# Check all matching files and VO tables are present
ras=[]
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
    Xfits_corr=re.sub(".fits","_corrected.fits",Xfits)
    Yfits_corr=re.sub(".fits","_corrected.fits",Yfits)
    Ifits_corr=re.sub(".fits","_corrected.fits",Ifits)
    if os.path.exists(Xfits_corr) and os.path.exists(Yfits_corr) and os.path.exists(Ifits_corr):
       print Xfits+" already corrected: not bothing to calculate."
#       files.remove(Xfits)
       docorr.append(False)
    else:
       docorr.append(True)
    if options.make_plots:
    # Get min and max RA, to see whether we need to unwrap, and set the plot limits
    # Surprised to find that WSClean uses negative RAs, which messes up the unwrap check
        crval1=fits.getheader(Ifits)['CRVAL1']
        if crval1 < 0.0:
            crval1+=360.0
        ras.append(crval1)

files_to_check=zip(files,docorr)

if options.make_plots:
# Padding around central RA and Dec -- roughly the field-of-view
    margin=4000000000./freq
    if max(ras)+margin-min(ras)-margin>300:
        unwrap=True
        ras=vunwrap(ras)
ratio=1.0

for Xfits,corr in files_to_check:

    ra=fits.getheader(Xfits)['CRVAL1']
    dec=fits.getheader(Xfits)['CRVAL2']
    freq=fits.getheader(Xfits)['CRVAL3']
    freq_str="%03.0f" % (freq/1e6)

# surely these filename substitutions can be made more pythonic
    Ifits=re.sub("XX","I",Xfits)
    Yfits=re.sub("XX","YY",Xfits)
# inputs
    Xpb=Xfits.replace(".fits","_pb.fits")
    Ypb=Xpb.replace("XX","YY")

    Xvot=Xpb.replace(".fits","_comp.vot")
    Yvot=Ypb.replace(".fits","_comp.vot")

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
                os.system('stilts tpipe in='+MRCvot+' cmd=\'select NULL_MFLAG\' cmd=\'addcol PA "0.0"\' cmd=\'addcol S_'+freq_str+' "S408*pow(('+str(freq)+'/408000000.0),-0.85)"\' out=temp1.vot')
                os.system('stilts tpipe in='+vot+' cmd=\'select local_rms<1.0\' out=temp2.vot')
                os.system('stilts tmatch2 matcher=skyellipse params=30 in1=temp1.vot in2=temp2.vot out=temp.vot values1="_RAJ2000 _DEJ2000 e_RA2000 e_DE2000 PA" values2="ra dec a b pa" ofmt=votable')
            # Exclude extended sources
# weight is currently S/N
                os.system('stilts tpipe in=temp.vot cmd=\'select ((int_flux/peak_flux)<2)\' cmd=\'addcol logratio "(ln(S_'+freq_str+'/int_flux))"\' cmd=\'addcol weight "(int_flux/local_rms)"\' cmd=\'addcol delRA "(_RAJ2000-ra)"\' cmd=\'addcol delDec "(_DEJ2000-dec)"\' omode=out ofmt=vot out=temp3.vot')
                os.system('stilts tpipe in=temp3.vot cmd=\'select abs(delRA)<1.0\' out='+matchvot)
                os.remove('temp.vot')
                os.remove('temp1.vot')
                os.remove('temp2.vot')
                os.remove('temp3.vot')

# First do the ionospheric corrections, using the "I" table, since it has the best S/N
# Check the matched table actually has entries
    Imatchvot=Ifits.replace(".fits","_MRC.vot")
    t = parse_single_table(Imatchvot)
    if t.array.shape[0]>0:

    # Calculate ionospheric offsets
        delRA=numpy.average(a=t.array['delRA'],weights=(t.array['weight'])) #*(distfunc)))
        delDec=numpy.average(a=t.array['delDec'],weights=(t.array['weight'])) #*(distfunc)))
        delRAstdev=numpy.std(a=t.array['delRA'])
        delDecstdev=numpy.std(a=t.array['delDec'])

    # Now calculate the correction factors for the I, XX and YY snapshots
        for pb in Ifits,Xpb,Ypb:
            image = pb.replace("_pb.fits",".fits")
            matchvot = pb.replace(".fits","_MRC.vot")
            t = parse_single_table(matchvot)
            if t.array.shape[0]>0:
                ratio=numpy.exp(numpy.average(a=t.array['logratio'],weights=(t.array['weight']))) #*(distfunc)))
                stdev=numpy.std(a=t.array['logratio'])
                print "Ratio of "+str(ratio)+" between "+image+" and MRC."
                print "stdev= "+str(stdev)

                if corr:
                    # Write new NON-primary-beam-corrected fits files
                    hdu_in = fits.open(image)
                # Modify to fix ionosphere
                    hdr_in = hdu_in[0].header
                    hdr_in['CRVAL1'] = ra + delRA
                    hdr_in['CRVAL2'] = dec + delDec
                # Modify to fix flux scaling
                    hdu_in[0].data=hdu_in[0].data*ratio
                # Remove stupid bonus keywords, if they have been added
                    try:
                        hdr_in.remove('DATAMIN')
                        hdr_in.remove('DATAMAX')
                    except:
                        pass
                # Write out
                    fits_corr=image.replace(".fits","_corrected.fits")
                    hdu_in.writeto(fits_corr,clobber=True)
                    f.write("{0:s} {1:10.8f} {2:10.8f} {3:10.8f} {4:10.8f} {5:10.8f} {6:10.8f}\n".format(image,delRA,delRAstdev,delDec,delDecstdev,ratio,stdev))
            else:
                print pb+" had no valid matches with MRC. Moving it to unused/ ."
                shutil.move(pb,"./unused/")

    if options.make_plots:
        outputpng=Iroot+"_vect.png"
    # Plot vectors
        if unwrap:
            X=vunwrap(t.array['_RAJ2000'])
            U=vunwrap(t.array['ra'])
        else:
            X=t.array['_RAJ2000']
            U=t.array['ra']
        Y=t.array['_DEJ2000']
        V=t.array['dec']
        fig=plt.figure(figsize=(20, 10))
        fig.suptitle(Iroot)
        ax = plt.gca()
        M = numpy.arctan((V-Y)/(U-X))
        ax.quiver(X,Y,60*(U-X),60*(V-Y),M,angles='xy',scale_units='xy',scale=1)
        ax.set_xlim([min(ras)-margin,max(ras)+margin])
        umargin=plotdec+margin
        #if umargin > 90.0:
        #    umargin=90.0
        #umargin=plotdec+margin*numpy.cos(numpy.deg2rad(umargin))
        if umargin > 90.0:
            umargin=90.0
        lmargin=plotdec-margin
        #if lmargin < -90.0:
        #    lmargin=-90.0
        #lmargin=plotdec-margin*numpy.cos(numpy.deg2rad(lmargin))
        if lmargin < -90.0:
            lmargin=-90.0
        ax.set_ylim([lmargin,umargin])
        ax.set_ylabel('Declination (deg)')
        ax.set_xlabel('RA (deg)')
        plt.savefig(outputpng)

f.close()
