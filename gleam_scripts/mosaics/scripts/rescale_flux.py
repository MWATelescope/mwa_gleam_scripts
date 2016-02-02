#!/usr/bin/env python

# Rescale a fits image by the factor in the zerofits table
# As long as there is only one entry!

import sys
from numpy import nonzero, exp
from astropy.io import fits
from optparse import OptionParser

usage="Usage: %prog [options]\n"
parser = OptionParser(usage=usage)
parser.add_option('--mosaic',type="string", dest="mosaic",default=None,
                    help="The filename of the mosaic you want to read in.")
parser.add_option('--zerofits',type="string", dest="zerofits",default=None,
                    help="The filename of the zerofits file you want to use.")
parser.add_option('--output',type="string", dest="output",default=None,
                    help="The output filename (default = input_rescaled.fits).")
parser.add_option('--multiply',action="store_true",dest="multiply",default=True,
                    help="Multiply instead of divide (default = True).")
parser.add_option('--divide',action="store_false",dest="multiply",default=True,
                    help="Divide instead of multiply (default = False).")
(options, args) = parser.parse_args()

if options.mosaic and options.zerofits:
    input=options.mosaic
    zerofits=options.zerofits

    hdu_in=fits.open(zerofits)
    tbdata=hdu_in[1].data
    factor=exp(tbdata.field('a')[nonzero(tbdata.field('a'))[0][0]])

    hdu_in=fits.open(input)
    if options.output:
        output=options.output
    else:
        output=input.replace(".fits","_rescaled.fits")
    
    if options.multiply:
        print "Multiplying by a factor of "+str(factor)+"."
        hdu_in[0].data*=factor
    else:
        print "Dividing by a factor of "+str(factor)+"."
        hdu_in[0].data/=factor
    hdu_in.writeto(output,clobber=True)
else:
    print "Mosaic and zerofits file to use must be specified."
    sys.exit(1)
