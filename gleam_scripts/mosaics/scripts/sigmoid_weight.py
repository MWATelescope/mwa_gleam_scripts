#!/usr/bin/python

import numpy as n

import os
import re
import glob

import astropy.io.fits as fits
from astropy import wcs

#tables and votables
from astropy.io.votable import parse_single_table

from optparse import OptionParser

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('--mosaic',type="string", dest="mosaic",
                    help="The filename of the mosaic you want to read in.")
parser.add_option('--output',type="string", dest="output", default=None,
                    help="The output filename. Default = input_sigmoid.fits")
(options, args) = parser.parse_args()

input_mosaic=options.mosaic

dec_zenith=-26.7

cutdir=os.environ['MWA_CODE_BASE']
centre_dec, freq_band, RA_lim1, RA_lim2, Dec_lim1, Dec_lim2 = n.loadtxt(cutdir+'/ra_dec_limits_polyderivation.dat',skiprows=2,unpack=True)

dec_freq_comb = [centre_dec, freq_band]

def wfunc(x,d,lowerlimit,upperlimit):
    if ((n.log(99)/d)+lowerlimit) < x < (upperlimit-(n.log(99)/d)):
        return 1.0
    else:
        if x < (n.log(99)/d)+lowerlimit:
            return n.sqrt(1+n.exp(-d*(x-lowerlimit)))
        if x > upperlimit-(n.log(99)/d):
            return n.sqrt(1+n.exp(d*(x-upperlimit)))
vwfunc=n.vectorize(wfunc)

# Get the dec cuts
header = fits.getheader(input_mosaic)
try:
    freq_obs = header['CRVAL3']/1e6
except:
    freq_obs = header['FREQ']/1e6
if 72. < freq_obs < 103.:
    subband = 1
elif 103.01 < freq_obs < 134.:
    subband = 2
elif 139. < freq_obs < 170.:
    subband = 3
elif 170.01 < freq_obs < 200.:
    subband = 4
elif 200.01 < freq_obs < 231.:
    subband = 5
Dec_strip = header['CRVAL2']

# These won't be listed in the file -- need to calculate the relevant cuts
if Dec_strip == -40. or Dec_strip == -55. or Dec_strip == -72. :
    if Dec_strip == -40.:
        dec_centre = -13.
    if Dec_strip == -55.:
        dec_centre = 1.6
    if Dec_strip == -72.:
        dec_centre = 18.6
    cut_ind = n.where((centre_dec == dec_centre) & (freq_band == subband))
# Mirror the relevant cuts over the zenith
    new_Dec_lim2 = dec_zenith+(dec_zenith-Dec_lim1[cut_ind])
    new_Dec_lim1 = dec_zenith+(dec_zenith-Dec_lim2[cut_ind])
    Dec_lim2=new_Dec_lim2
    Dec_lim1=new_Dec_lim1
# Don't bother downweighting the bottom edge of Dec-72
    if Dec_strip == -72:
        Dec_lim1 = -90.0
    print "Dec strip "+str(Dec_strip)+": using mirrored indices for "+str(dec_centre)+": "+str(Dec_lim1)+" to "+str(Dec_lim2)
# Zenith Dec -35 hard cut is incorrect for these purposes; better to use Dec-13 but shifted by 14 deg
elif Dec_strip == -26.7 or Dec_strip == -27.0:
    dec_centre = -13.
    cut_ind = n.where((centre_dec == dec_centre) & (freq_band == subband))
    Dec_lim1 = Dec_lim1[cut_ind]+(dec_zenith-dec_centre)
    Dec_lim2 = Dec_lim2[cut_ind]+(dec_zenith-dec_centre)
    print "Dec strip "+str(Dec_strip)+": using shifted indices for "+str(dec_centre)+": "+str(Dec_lim1)+" to "+str(Dec_lim2)
else:
    dec_centre = Dec_strip
    cut_ind = n.where((centre_dec == dec_centre) & (freq_band == subband))
    Dec_lim1 = Dec_lim1[cut_ind]
    Dec_lim2 = Dec_lim2[cut_ind]
# Don't bother downweighting the top edge of Dec+18
    if Dec_strip == +18.6:
        Dec_lim2 = +90.0
    print "Dec strip "+str(Dec_strip)+": using standard indices for "+str(dec_centre)+": "+str(Dec_lim1)+" to "+str(Dec_lim2)

if options.output:
    sigmoid=options.output
else:
    sigmoid=re.sub(".fits","_sigmoid.fits",os.path.basename(input_mosaic))

if os.path.isfile(sigmoid):
    os.remove(sigmoid)

# Modify the RMS file so that it is multiplied by a function which is
# 1 between Dec_lim1 and Dec_lim2
# Transitions into a sigmoid function which drops to 1% across 4 degrees (d=2), centred on each Dec_lim
# In RMS space, that's 1/sqrt(sigmoid)

hdu_in=fits.open(input_mosaic)
# Fixing header problem. Removing third axis.
try:
    test=hdu_in[0].header['CRPIX3']
except:
    test=False
if test:
    del hdu_in[0].header['CRPIX3']
    del hdu_in[0].header['CRVAL3']
    del hdu_in[0].header['CDELT3']
    del hdu_in[0].header['CUNIT3']
    del hdu_in[0].header['CTYPE3']

# wcs in format [x,y,stokes,freq]; stokes and freq are length 1 if they exist
w=wcs.WCS(hdu_in[0].header)

#create an array but don't set the values (they are random)
indexes = n.empty( (hdu_in[0].data.shape[0]*hdu_in[0].data.shape[1],2),dtype=int)
#since I know exactly what the index array needs to look like I can construct
# it faster than list comprehension would allow
#we do this only once and then recycle it
idx = n.array([ (j,0) for j in xrange(hdu_in[0].data.shape[1])])
j=hdu_in[0].data.shape[1]
for i in xrange(hdu_in[0].data.shape[0]):
    idx[:,1]=i
    indexes[i*j:(i+1)*j] = idx
#put ALL the pixles into our vectorized functions and minimise our overheads
ra,dec = w.wcs_pix2world(indexes,1).transpose()
wcorr=vwfunc(dec,4,Dec_lim1,Dec_lim2)
reshapedwcorr=wcorr.reshape(hdu_in[0].data.shape[0],hdu_in[0].data.shape[1])
hdu_in[0].data=reshapedwcorr*hdu_in[0].data
hdu_in.writeto("./"+sigmoid)
hdu_in.close()
