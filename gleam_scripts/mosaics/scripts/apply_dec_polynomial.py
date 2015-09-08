#!/usr/bin/env python

# Applying the polynominal correction derived from decfluxdependence_derive.py.
# Note that this should be run from directory structure that is above saving directories.

import numpy as np
import matplotlib as plt
from astropy.io import fits
from astropy import wcs
from optparse import OptionParser
import os
import sys
import re

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('--mosaic',type="string", dest="mosaic",
                    help="The filename of the mosaic you want to read in.")
(options, args) = parser.parse_args()

input_mosaic = options.mosaic
input_root=input_mosaic.replace(".fits","")

header = fits.getheader(input_mosaic)
try:
    freq_obs = header['CRVAL3']/1e6
    modheader=True
except:
    freq_obs = header['FREQ']/1e6
    modheader=False
Dec_strip = header['CRVAL2']

hdu_in=fits.open(input_mosaic)

dec_zenith = -26.7
# Week 1.1
# 20130808 +1.6 -- Some GP at start, ionosphere horrible later
# 20130809 -55
# 20130810 -27 -- Good.
# 20130817 +18.6  --- Cygnus at start, ionosphere at the end
# 20130818 -72
# 20130822 -13 -- Fine. Better than week 1.2. <------------ use this one
# 20130825 -40

# Week 1.2
# 20131105 -13 -- Ionospheric blurring at the lowest frequencies
# 20131106 -40
# 20131107 +1.6 -- Fine <------------ use this one
# 20131108 -55
# 20131111 +18.6 -- Fine <----------- use this one
# 20131112 -72
# 20131125 -27 Crab is a contaminant for middle channels -- but still gives lower reduced chi2 than week 1.1 <-- use

# Week 1.3
# 20140303 -27 -- 1/3rd of fibre flagged on Rec 6 (don't transfer these sols)
# 20140304 -13 -- Fine.
# 20140306 +1.6 -- 1/3rd of fibre flagged on Rec 6 (don't transfer these sols)
# 20140308 +18.6 -- Virgo A very tough (don't transfer these sols)
# 20140309 -72 -- unknown
# 20140316 -40 -- only between GP and CenA
# 20140317 -55 -- only between GP and CenA
# So get ALL of these solutions from other weeks

week=input_root.split("_")[1][0:6]

if Dec_strip == -40. or Dec_strip == -55. or Dec_strip == -72. or ( week != "20131107" and week != "20131111" and week != "20131125" and week != "20130822" ):
    if Dec_strip == -40. or Dec_strip == -13.:
        input_mosaic_polyfit = re.sub("201[0-9]{5}","20130822",input_root)
        poly_path = re.sub("201[0-9]{5}","20130822",os.getcwd())
    if Dec_strip == -55. or Dec_strip == 1.6 or Dec_strip == 2. or Dec_strip == 1.:
        input_mosaic_polyfit = re.sub("201[0-9]{5}","20131107",input_root)
        poly_path = re.sub("201[0-9]{5}","20131107",os.getcwd())
    if Dec_strip == -72. or Dec_strip == 18.6 or Dec_strip == 19. or Dec_strip == 18.:
        input_mosaic_polyfit = re.sub("201[0-9]{5}","20131111",input_root)
        poly_path = re.sub("201[0-9]{5}","20131111",os.getcwd())
    if Dec_strip == -26.7 or Dec_strip == -27. or Dec_strip == -26.:
        input_mosaic_polyfit = re.sub("201[0-9]{5}","20131125",input_root)
        poly_path = re.sub("201[0-9]{5}","20131125",os.getcwd())
    hdulist = fits.open(poly_path+'/'+input_mosaic_polyfit+'_simple_coefficients.fits')
    print 'Using corrections from '+poly_path+'/'+input_mosaic_polyfit+'_simple_coefficients.fits'
else:
    hdulist = fits.open(input_root+'_simple_coefficients.fits')

hdulist.verify('fix')
tbdata = hdulist[1].data
hdulist.close()

a  = np.array(tbdata['a'])
b  = np.array(tbdata['b'])
c  = np.array(tbdata['c'])
d  = np.array(tbdata['d'])

    # wcs in format [x,y,stokes,freq]; stokes and freq are length 1 if they exist
w=wcs.WCS(hdu_in[0].header)

#create an array but don't set the values (they are random)
indexes = np.empty( (hdu_in[0].data.shape[0]*hdu_in[0].data.shape[1],2),dtype=int)
#since I know exactly what the index array needs to look like I can construct
# it faster than list comprehension would allow
#we do this only once and then recycle it
idx = np.array([ (j,0) for j in xrange(hdu_in[0].data.shape[1])])
j=hdu_in[0].data.shape[1]
for i in xrange(hdu_in[0].data.shape[0]):
    idx[:,1]=i
    indexes[i*j:(i+1)*j] = idx
#put ALL the pixles into our vectorized functions and minimised our overheads
ra,dec = w.wcs_pix2world(indexes,1).transpose()
if Dec_strip == -40. or Dec_strip == -55. or Dec_strip == -72.:
    print "Applying mirror correction to Dec"+str(Dec_strip)
    # Reflecting cubic around the x-axis and shifting to new centre dec
    corr=np.exp(-d[0]*np.power((dec-(2*dec_zenith)),3)+c[0]*np.power((dec-(2*dec_zenith)),2)-b[0]*((dec-(2*dec_zenith)))+a[0])
else:
    print "Applying normal correction to Dec"+str(Dec_strip)
    corr=np.exp(d[0]*np.power(dec,3)+c[0]*np.power(dec,2)+b[0]*dec+a[0])

reshapedcorr=corr.reshape(hdu_in[0].data.shape[0],hdu_in[0].data.shape[1])
hdu_in[0].data=np.array(reshapedcorr*hdu_in[0].data,dtype=np.float32)
hdu_in.writeto(input_root+'_polyapplied.fits',clobber=True)
hdu_in.close(input_root+'_polyapplied.fits')
