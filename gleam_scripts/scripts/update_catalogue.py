#!/usr/bin/env python

import numpy as np
import scipy
import scipy.stats
import math
import os, sys, re

from astropy.io.votable import parse_single_table
from astropy.io.votable import writeto as writetoVO
from astropy.table import Table, Column

from astropy.io import fits
from astropy import wcs

from optparse import OptionParser

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('--catalogue',dest="catalogue",default=None,
                  help="Catalogue to update.")
parser.add_option('--psfimage',dest="psfimage",default=None,
                  help="Input PSF image to use (default = catalogue_int_peak.fits).")
parser.add_option('--aimage',dest="aimage",default=None,
                  help="Input major axis (a) image to use (default = catalogue_a.fits).")
parser.add_option('--bimage',dest="bimage",default=None,
                  help="Input minor axis (b) image to use (default = catalogue_b.fits).")
parser.add_option('--paimage',dest="paimage",default=None,
                  help="Input position angle (pa) image to use (default = catalogue_pa.fits).")
parser.add_option('--output',dest="output",default=None,
                  help="Output catalogue file (default = catalogue_mod.vot).")
(options, args) = parser.parse_args()

# Parse the input options

if not os.path.exists(options.catalogue):
    print "Error! Must specify an input catalogue."
    sys.exit(1)
else:
    catfile=options.catalogue
    if options.psfimage:
        psfimage=options.psfimage
    else:
        psfimage=catfile.replace('_comp.vot','_int_peak.fits')
    if options.aimage:
        aimage=options.aimage
    else:
        aimage=catfile.replace('_comp.vot','_a.fits')
    if options.bimage:
        bimage=options.bimage
    else:
        bimage=catfile.replace('_comp.vot','_b.fits')
    if options.paimage:
        paimage=options.paimage
    else:
        paimage=catfile.replace('_comp.vot','_pa.fits')
    if options.output:
        output=options.output
    else:
        output=catfile.replace('_comp.vot','_mod.vot')

# Read the VO table and start processing

table = parse_single_table(catfile)
data = table.array

psf_in = fits.open(psfimage)
w = wcs.WCS(psf_in[0].header,naxis=2)

unmara, unmadec = np.array(data['ra']).tolist(), np.array(data['dec']).tolist()
rapix, decpix = w.wcs_world2pix(unmara,unmadec,1)
raintpix, decintpix = np.array(np.round(rapix),dtype=int), np.array(np.round(decpix),dtype=int)
raclip, decclip = np.clip(raintpix,0,psf_in[0].data.shape[1]-1), np.clip(decintpix,0,psf_in[0].data.shape[0]-1)
# Yes, it's bonkers that the wcs is the other way round compared to the fits file
psf_ratio = psf_in[0].data[decclip,raclip]

# Scale the integrated fluxes
data['int_flux']/=psf_ratio
vot = Table(data)

# Get the PSF information
a_in = fits.open(aimage)
b_in = fits.open(bimage)
pa_in = fits.open(paimage)
a = a_in[0].data[decclip,raclip]
b = b_in[0].data[decclip,raclip]
pa = pa_in[0].data[decclip,raclip]

# Add the PSF columns
vot.add_column(Column(data=a,name='a_psf'))
vot.add_column(Column(data=b,name='b_psf'))
vot.add_column(Column(data=pa,name='pa_psf'))

# description of this votable
vot.description = "Corrected for PSF variation"
writetoVO(vot, output)
