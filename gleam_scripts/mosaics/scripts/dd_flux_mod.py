#!/usr/bin/env python

# Read in the PSF map
# Divide out the elevation dependence of the volume increase
# Multiply the non-rescaled map by (a*b)/(a_theory*b_theory)

# Then when I rerun the flux-calibration, using the PSF map, it should be correct

import numpy as np

from astropy.io import fits
from astropy import wcs
from optparse import OptionParser

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('--mosaic',type="string", dest="mosaic",
                    help="The filename of the mosaic you want to read in.")
parser.add_option('--psf',type="string", dest="psf",
                    help="The filename of the psf image you want to read in.")
parser.add_option('--output',type="string", dest="output",
                    help="The filename of the output rescaled image.")
(options, args) = parser.parse_args()

latitude=-26.70331940

input_mosaic = options.mosaic
input_root=input_mosaic.replace(".fits","")

# Read in the mosaic to be modified
mosaic = fits.open(input_mosaic)
w = wcs.WCS(mosaic[0].header)

#create an array but don't set the values (they are random)
indexes = np.empty( (mosaic[0].data.shape[0]*mosaic[0].data.shape[1],2),dtype=int)
#since I know exactly what the index array needs to look like I can construct
# it faster than list comprehension would allow
#we do this only once and then recycle it
idx = np.array([ (j,0) for j in xrange(mosaic[0].data.shape[1])])
j=mosaic[0].data.shape[1]
for i in xrange(mosaic[0].data.shape[0]):
    idx[:,1]=i
    indexes[i*j:(i+1)*j] = idx

#put ALL the pixels into our vectorized functions and minimise our overheads
ra,dec = w.wcs_pix2world(indexes,1).transpose()

# Get the header (nominal) BMAJ and BMIN

bmaj = mosaic[0].header['BMAJ']
bmin = mosaic[0].header['BMIN']

# Read in the PSF
psf = fits.open(options.psf)
#a = psf[0].data[0]
#b = psf[0].data[1]
blur = psf[0].data[3]
#pa = psf[0].data[2]

w_psf = wcs.WCS(psf[0].header,naxis=2)

##create an array but don't set the values (they are random)
#indexes = np.empty( (psf[0].data.shape[1]*psf[0].data.shape[2],2),dtype=int)
##since I know exactly what the index array needs to look like I can construct
## it faster than list comprehension would allow
##we do this only once and then recycle it
#idx = np.array([ (j,0) for j in xrange(psf[0].data.shape[2])])
#j=psf[0].data.shape[2]
#for i in xrange(psf[0].data.shape[1]):
#    idx[:,1]=i
#    indexes[i*j:(i+1)*j] = idx
#
#ra_psf,dec_psf = w_psf.wcs_pix2world(indexes,1).transpose()
#za_psf = latitude - dec_psf
#
#corr = np.cos(np.radians(za_psf))
#reshapedcorr=corr.reshape(psf[0].data.shape[1],psf[0].data.shape[2])
#
## Test file: write out number we will multiply by
##psf[0].data[0]=a*b*reshapedcorr/(bmaj*bmin)
##psf.writeto('test.fits',clobber=True)
#
#blur = a*b*reshapedcorr/(bmaj*bmin)

# Now need to correct the original mosaic based on its (RA, Dec) co-ordinates.

# First write it in a loop style so I can get my head around it

#for i, j in mosaic[0].data:
#   ra_tmp , dec_tmp = w.wcs_pix2world([[i,j]],1).transpose()
#   k, l = w_psf.wcs_world2pix([[ra_tmp[0],dec_tmp[0]]],1).transpose()
#   mosaic[0].data[i,j]*=blur[k[0],l[0]]

# Now in a non-looped way
k, l = w_psf.wcs_world2pix(ra,dec,1)
k_int = [np.floor(x) for x in k]
k_int = [x if (x>=0) and (x<=360) else 0 for x in k_int]
l_int = [np.floor(x) for x in l]
l_int = [x if (x>=0) and (x=<180) else 0 for x in l_int]
blur_tmp = blur[l_int,k_int]
blur_corr = blur_tmp.reshape(mosaic[0].data.shape[0],mosaic[0].data.shape[1])
mosaic[0].data*=blur_corr

mosaic.writeto(options.output,clobber=True)
