#!/usr/bin/env python

import sys
import glob
try:
    import astropy.io.fits as pyfits
except ImportError:
    import pyfits
from optparse import OptionParser
from numpy import nanstd, nanmean 

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('--corners',action="store_true",dest="corners",
                  help="Use the four corners to measure the rms?")
parser.add_option('--middle',action="store_false",dest="corners",
                  help="Use the middle of the image to measure the rms?")
parser.add_option('--mean',action="store_true",dest="mean",default=False,
                  help="Report the mean of the data instead of the rms (useful for images of the rms).")
# 300 pixels is a good compromise between speed, excluding undeconvolved sources, and getting enough pixels to make a sensible measurement
parser.add_option('--boxsize',dest="side",default=300,type=int,
                  help="Set the box side size in pixels; default = 300x300 pixels")
(options, args) = parser.parse_args()

side=options.side

files=sorted([f for f in glob.glob("10*2.?_corrected.fits") if "XX" in f or "YY" in f])

for filename in files:
    rms=[]
    hdulist = pyfits.open(filename)
    if hdulist[0].data.shape[0]>1:
        #format is e.g. RA, Dec, stokes, spectral -- unusual for MWA images
        totlen=hdulist[0].data.shape[0]
        sfxy=False
    else:
        # format is e.g. stokes, spectral, RA, Dec -- usual for MWA images
        totlen=hdulist[0].data.shape[2]
        sfxy=True

    scidata=[]
    if totlen>0:
        if options.corners:
            if sfxy:
                scidata.append(hdulist[0].data[:,:,totlen-side:totlen,totlen-side:totlen][0][0])
                scidata.append(hdulist[0].data[:,:,0:side,totlen-side:totlen][0][0])
                scidata.append(hdulist[0].data[:,:,totlen-side:totlen,0:side][0][0])
                scidata.append(hdulist[0].data[:,:,0:side,0:side][0][0])
            else:
                scidata.append(hdulist[0].data[totlen-side:totlen,totlen-side:totlen][0][0])
                scidata.append(hdulist[0].data[0:side,totlen-side:totlen][0][0])
                scidata.append(hdulist[0].data[totlen-side:totlen,0:side][0][0])
                scidata.append(hdulist[0].data[0:side,0:side][0][0])
        else:
            half=int(totlen/2)
            if sfxy:
                scidata=hdulist[0].data[:,:,half-side:half+side,half-side:half+side]
            else:
                scidata=hdulist[0].data[half-side:half+side,half-side:half+side]
        if options.mean:
            imagerms=nanmean(scidata)
        else:
            imagerms=nanstd(scidata)
    hdulist[0].header['IMAGERMS'] = imagerms
    hdulist.writeto(filename, clobber=True)
