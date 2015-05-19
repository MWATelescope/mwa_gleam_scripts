#!/usr/bin/python

# A tool to make masks into zeroes

import numpy as np
from astropy.io import fits
import sys,re
from optparse import OptionParser

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('-i','--input',dest="fin",default=None,
                  help="input <FILE>",metavar="FILE")
parser.add_option('-o','--output',dest="fout",default=None,
                  help="output <FILE> default=input_unmask.fits",metavar="FILE")

(options, args) = parser.parse_args()

if options.fin:
    fin=options.fin
else:
    print "Must specify an input filename."
    sys.exit()

if options.fout:
    fout=options.fout
else:
    fout=re.sub(".fits","_unmask.fits",fin)

hdulist = fits.open(fin)

# Zero masked pixels
hdulist[0].data[np.isnan(hdulist[0].data)]=0.0

# Save resized fits file
hdulist.writeto(fout,clobber=True)
print "wrote",fout
