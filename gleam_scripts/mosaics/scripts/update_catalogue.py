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
parser.add_option('--average',action="store_true",dest="average",default=False,
                  help="Use the average PSF to correct the catalogue, instead of using the position-dependent corrections. (default = False).")
parser.add_option('--output',dest="output",default=None,
                  help="Output catalogue file (default = catalogue_mod.vot, or catalogue_ddmod.vot for direction-dependent corrections).")
parser.add_option('--scalefits',action="store_true",dest="scalefits",default=False,
                  help="Scale fits image beam in header (default = False).")
parser.add_option('--fitsimage',dest="fitsimage",default=None,
                  help="Fitsimage to update (header) (default = get from catalogue name).")
parser.add_option('--outfits',dest="outfits",default=None,
                  help="Output fits image file with new beam in header (default = fitsimage_mod.fits).")

(options, args) = parser.parse_args()

# No scipy option for weighted gmean so write my own

def wgmean(a,weights):
    total=np.sum(weights*np.log(a))
    sum_of_weights=np.sum(weights)
    weighted_geometric_mean=np.exp(total/sum_of_weights)
    return weighted_geometric_mean

# Parse the input options

if not os.path.exists(options.catalogue):
    print "Error! Must specify a valid input catalogue."
    sys.exit(1)
else:
    catfile=options.catalogue
    psfcat=catfile.replace('_comp.vot','_psf.vot')
    print "Using PSF catalogue for average corrections: "+psfcat
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
        if options.average:
            output=catfile.replace('_comp.vot','_mod.vot')
        else:
            output=catfile.replace('_comp.vot','_ddmod.vot')
    if options.fitsimage:
        fitsimage=options.fitsimage
    else:
        fitsimage=catfile.replace('_comp.vot','.fits')
        if not os.path.exists(fitsimage):
            tempvar=catfile.split("_")
            fitsimage=tempvar[0]+"_"+tempvar[1]+".fits"
        if options.outfits:
            outfits=options.outfits
        else:
            outfits=fitsimage.replace('.fits','_mod.fits')
        print "Modifying "+fitsimage+" to write modified header to fits image: "+outfits

# Read the VO table and start processing

table = parse_single_table(catfile)
data = table.array

psf_table = parse_single_table(psfcat)
psf_data = psf_table.array
psf_ratio=np.average(a=(psf_data['int_flux']/psf_data['peak_flux']),weights=(np.power(psf_data['peak_flux']/psf_data['local_rms'],2)))
#    print "Average psf_ratio = "+str(psf_ratio)
#    psf_ratio=wgmean(a=(psf_data['int_flux']/psf_data['peak_flux']),weights=(np.power(psf_data['peak_flux']/psf_data['local_rms'],2)))
#    print "Weighted geometric mean psf_ratio = "+str(psf_ratio)
#    psf_ratio=scipy.stats.gmean(a=(psf_data['int_flux']/psf_data['peak_flux']))
#    print "Unweighted geometric mean psf_ratio = "+str(psf_ratio)
if options.scalefits:
    print "Simply scaling the fits header beam by a direction-independent factor of "+str(psf_ratio)
    hdu_in=fits.open(fitsimage)
    hdu_in[0].header['BMAJ']*=psf_ratio
    hdu_in[0].header['BMIN']*=psf_ratio
    print "Writing to "+outfits
    hdu_in.writeto(outfits, clobber=True)

if options.average:
    print "Simply scaling the peak fluxes in the catalogue by a direction-independent factor of "+str(psf_ratio)
    data['peak_flux']*=psf_ratio
    vot = Table(data)
    # description of this votable
    vot.description = "Corrected for position-independent PSF variation"
    print "Writing to "+output
    writetoVO(vot, output)
else:
    print "Performing direction-dependent PSF correction."
    psf_in = fits.open(psfimage)
    w = wcs.WCS(psf_in[0].header,naxis=2)

    unmara, unmadec = np.array(data['ra']).tolist(), np.array(data['dec']).tolist()
    rapix, decpix = w.wcs_world2pix(unmara,unmadec,1)
    raintpix, decintpix = np.array(np.round(rapix),dtype=int), np.array(np.round(decpix),dtype=int)
    raclip, decclip = np.clip(raintpix,0,psf_in[0].data.shape[1]-1), np.clip(decintpix,0,psf_in[0].data.shape[0]-1)
    # Yes, it's bonkers that the wcs is the other way round compared to the fits file
    psf_ratio = psf_in[0].data[decclip,raclip]

    # Get the PSF information
    a_in = fits.open(aimage)
    b_in = fits.open(bimage)
    pa_in = fits.open(paimage)
    a = a_in[0].data[decclip,raclip]
    b = b_in[0].data[decclip,raclip]
    pa = pa_in[0].data[decclip,raclip]

    # Scale the peak fluxes
    data['peak_flux']*=psf_ratio

    vot = Table(data)

    # Add the PSF columns
    vot.add_column(Column(data=a,name='a_psf'))
    vot.add_column(Column(data=b,name='b_psf'))
    vot.add_column(Column(data=pa,name='pa_psf'))

    # description of this votable
    vot.description = "Corrected for position-dependent PSF variation"
    print "Writing to "+output
    writetoVO(vot, output)
