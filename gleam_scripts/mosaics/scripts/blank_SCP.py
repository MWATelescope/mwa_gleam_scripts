#!/usr/bin/env python

import sys
import numpy as np
import math

try:
    import astropy.io.fits as pyfits
except ImportError:
    import pyfits

from astropy import wcs
from optparse import OptionParser

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('-r','--radius',dest="flag_radius",default=60.0,
                  help="Radius in degrees to be flagged (default = 4 hours = 60 degrees)")
parser.add_option('-f','--filename',dest="filename",default=None,
                  help="Input file to blank <FILE>",metavar="FILE")
parser.add_option('-o','--output',dest="output",default=None,
                  help="Output file <FILE>",metavar="FILE")
(options, args) = parser.parse_args()

# For unwrapping RA values which bridge the meridian
def unwrap(x):
    if x>180:
        return x-360
    else:
        return x
vunwrap=np.vectorize(unwrap)

if options.filename is None:
    print "Must supply a filename"
    sys.exit(1)
else:
    if options.output:
        output=options.output
    else:
        output=options.filename.replace('.fits','_crop.fits')
    # Snapshot observation:
    # wcs in format [stokes,freq,x,y]; stokes and freq are length 1 if they exist
    hdu_in = pyfits.open(options.filename)
    original_shape=hdu_in[0].data.shape
    w = wcs.WCS(hdu_in[0].header,naxis=2)

    if len(original_shape)>2:
        scidata = np.squeeze(hdu_in[0].data)
    else:
        scidata=hdu_in[0].data

# Blank everything south of the pole
# More efficient to do this with a standard WCS call
    ycrd = w.wcs_world2pix([[0.0,-90]],1)[0][1]
# We get "whiskers" unless we aggressively round up, here.
    scidata[0:int(math.ceil(ycrd)),:]=np.nan

# Now blank everything within the RA range: better to do this like MIMAS
    #create an array but don't set the values (they are random)
    indexes = np.empty( (scidata.shape[0]*scidata.shape[1],2),dtype=int)
    #since I know exactly what the index array needs to look like I can construct
    # it faster than list comprehension would allow
    #we do this only once and then recycle it
    idx = np.array([ (j,0) for j in xrange(scidata.shape[1])])
    j=scidata.shape[1]
    for i in xrange(scidata.shape[0]):
        idx[:,1]=i
        indexes[i*j:(i+1)*j] = idx
#put ALL the pixels into our vectorized functions and minimise our overheads
    ra,dec = w.wcs_pix2world(indexes,1).transpose()

# Want to find out if we need to unwrap RA, by looking at the pixel above ycrd
    minra=w.wcs_pix2world([[3*scidata.shape[0]/4,ycrd+1]],1)[0][0]
    maxra=w.wcs_pix2world([[scidata.shape[0]/4,ycrd+1]],1)[0][0]
# WCS tends to be negative for snapshots for some reason
    if (minra < 0) or (maxra < 0):
        ra+=360.0
# And my unwrap function only works for +ve RAs
    if maxra < minra:
        ra=vunwrap(ra)
# So at the end of all that, if the meridian is in the image, RA must lie between -180 and +180
# So midra must also lie in that range
    midra=hdu_in[0].header['CRVAL1']
    if midra > 180.:
        midra-=360.

# Pixels to keep within RA range
    mask1d=np.ones(shape=ra.shape,dtype=np.float32)
    mask1d[np.where(ra<(midra-options.flag_radius))]=np.nan
    mask1d[np.where(ra>(midra+options.flag_radius))]=np.nan
    mask1d[np.where(np.bitwise_not(np.isfinite(ra)))]=np.nan

    mask2d=mask1d.reshape(scidata.shape[0],scidata.shape[1])
    hdu_in[0].data=(mask2d*scidata).reshape(original_shape)

    hdu_in.writeto(output,clobber=True)

