#!/usr/bin/env python

# Ridiculously, I need to rescale the RMS maps by a factor of ~1000-100000
# in order to avoid swarp blanking the weights
# due to a hard internal cutoff of around e-31.

import sys
from astropy.io import fits
from optparse import OptionParser

usage="Usage: %prog [options]\n"
parser = OptionParser(usage=usage)
parser.add_option('--mosaic',type="string", dest="mosaic",
                    help="The filename of the mosaic you want to read in.")
parser.add_option('--upscale',action="store_true",dest="upscale",default=False,
                    help="Scale the RMS back up instead of down (default = False).")
(options, args) = parser.parse_args()

if options.mosaic:
    hdu_in=fits.open(options.mosaic)
    if options.upscale:
        hdu_in[0].data*=1e6
    else:
        hdu_in[0].data/=1e6
    hdu_in.writeto(options.mosaic,clobber=True)
else:
    print "Mosaic must be specified."
    sys.exit(1)
