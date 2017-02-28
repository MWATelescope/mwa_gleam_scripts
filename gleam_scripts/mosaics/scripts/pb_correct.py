#!/usr/bin/env python

# Divide one input by another (useful for primary beam correction)

import sys
import os
from astropy.io import fits
from optparse import OptionParser

usage="Usage: %prog [options]\n"
parser = OptionParser(usage=usage)
parser.add_option('--input',type="string", dest="input",default=None,
                    help="The filename of the input you want to read in.")
parser.add_option('--output',type="string", dest="output",default=None,
                    help="The output filename (default = input_pb.fits).")
parser.add_option('--beam',type="string", dest="beam",default=None,
                    help="The beam filename")
parser.add_option('--divide',action="store_true",dest="divide",default=True,
                    help="Divide instead of multiply (default = True).")
parser.add_option('--multiply',action="store_false",dest="divide",
                    help="Multiply instead of divide (default = False).")
(options, args) = parser.parse_args()

if options.input and options.beam:
    input=options.input
    beam=options.beam
    if os.path.exists(input) and os.path.exists(beam):
        hdu_in=fits.open(input)
        beam_in=fits.open(beam)
    else:
        print "Missing an input."
        sys.exit(1)
    if options.output:
        output=options.output
    else:
        output=input.replace(".fits","_pb.fits")
    
    if options.divide:
        try:
            hdu_in[0].data/=beam_in[0].data
        except:
# For flattened fits files
            hdu_in[0].data/=beam_in[0].data[0][0]
    else:
        try:
            hdu_in[0].data*=beam_in[0].data
        except:
            hdu_in[0].data*=beam_in[0].data[0][0]
    hdu_in.writeto(output,clobber=True)
else:
    print "Input and beam must be specified."
    sys.exit(1)
