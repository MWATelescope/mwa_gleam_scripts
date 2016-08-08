#!/usr/bin/env python

# Plot specific source from GLEAM catalogue

import os, sys

# Need a least-squares estimator that gives a useable error estimate
from scipy.optimize import leastsq

import numpy as np
#tables and votables
import astropy.io.fits as fits
from astropy.io.votable import parse_single_table
from astropy.io.votable import writeto as writetoVO
from astropy.table import Table, Column

import matplotlib.pyplot as plt

from optparse import OptionParser

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('--catalogue',type="string", dest="catalogue",
                    help="The filename of the catalogue you want to read in.", default=None)
parser.add_option('--outpng',type="string", dest="outpng",
                    help="The filename of the output png.", default=None)
#parser.add_option('--plot',action="store_true",dest="make_plots",default=False,
#                  help="Make fit plots? (default = False)")
parser.add_option('--order',dest="poly_order",default=1,type=int,
                  help="Set the order of the polynomial fit. (default = 1)")
parser.add_option('--source',dest="source",default=None,type="string",
                  help="Name of the source to plot (use quotes)")
(options, args) = parser.parse_args()

# http://scipy-cookbook.readthedocs.org/items/FittingData.html
# Define function for calculating a power law
powerlaw = lambda x, amp, index: amp * (x**index)

# define our (line) fitting function
fitfunc = lambda p, x: p[0] + p[1] * x
errfunc = lambda p, x, y, err: (y - fitfunc(p, x)) / err

if options.source is None:
    print "Must select a source to plot!"
    sys.exit(1)
if options.outpng is None:
    outpng=(options.source.replace(" ","_"))+".png"
else:
    outpng=options.outpng

if options.catalogue is None:
    print "must specify input catalogue"
    sys.exit(1)
else:
    filename, file_extension = os.path.splitext(options.catalogue)
    if file_extension == ".fits":
        temp = fits.open(options.catalogue)
        data = temp[1].data
    elif file_extension == ".vot":
        temp = parse_single_table(options.catalogue)
        data = temp.array

# Frequencies to write out -- use the full band since it shows the range I did the fitting over
freq1=72
freq2=231

# Can't figure out how to read the bloody column names! hardcode
freqs=["076", "084", "092", "099", "107",  "115", "122", "130", "143", "151", "158", "166", "174",  "181", "189","197", "204", "212", "220", "227"]
#freqs=["204", "212", "220", "227"]
#freqs=["76", "84", "92", "99", "107",  "115", "122", "130", "143", "151", "158", "166", "174",  "181", "189","197", "204", "212", "220", "227"]


index = np.where(data["Name"]==options.source)
# select fluxes
flux_list = []
for x in freqs:
    flux_list.append(np.ma.log(data["int_flux_"+x][index]))
flux_array = np.ravel(np.asarray(flux_list))

err_list = []
for x in freqs:
    err_list.append(data["err_int_flux_"+x][index]/data["int_flux_"+x][index])
flux_errors = np.ravel(np.asarray(err_list))

weights = 1/(flux_errors*flux_errors)
freq_array = np.log(np.ma.array([float(int(x)) for x in freqs]),dtype="float32")

print freq_array
print flux_array
print flux_errors
pinit = [-2.0, -0.7]
fit = leastsq(errfunc, pinit, args=(freq_array, flux_array, flux_errors), full_output=1)
# Just checking using numpy's polyfit
#    npP=np.ma.polyfit(freq_array,flux_array[i],options.poly_order,w=1/flux_errors[i])
#    npalpha = npP[0]
#    npamp = np.exp(npP[1])
covar = fit[1]
if covar is not None:
    P = fit[0]
    alpha=P[1]
    amp = np.exp(P[0])
    flux1=powerlaw(freq1,amp,alpha)
    flux2=powerlaw(freq2,amp,alpha)
# Errors
    err_alpha = np.sqrt(covar[0][0])
    err_flux1 = np.sqrt(covar[1][1])*flux1
    err_flux2 = np.sqrt(covar[1][1])*flux2
else:
    alpha=None
    amp=None
    flux1=None
    flux2=None
    err_alpha=None
    err_flux1=None
    err_flux2=None

#indices = np.where(np.bitwise_not(np.isnan(alpha)))

# Plot
example=plt.figure(figsize=(5,10))
ax1=example.add_subplot(2,1,1)
ax1.plot(np.exp(freq_array), powerlaw(np.exp(freq_array), amp, alpha))     # Fit
#ax1.plot(np.exp(freq_array), powerlaw(np.exp(freq_array), npamp, npalpha))     # Fit
ax1.errorbar(np.exp(freq_array), np.exp(flux_array), yerr=flux_errors*np.exp(flux_array), fmt='k.')  # Data
ax2=example.add_subplot(2,1,2)
ax2.loglog(np.exp(freq_array), powerlaw(np.exp(freq_array), amp, alpha))     # Fit
#ax2.loglog(np.exp(freq_array), powerlaw(np.exp(freq_array), npamp, npalpha))     # Fit
ax2.errorbar(np.exp(freq_array), np.exp(flux_array), yerr=flux_errors*np.exp(flux_array), fmt='k.')  # Data
ax2.set_xlim([min(np.exp(freq_array)),max(np.exp(freq_array))])
ax2.set_ylim([min(np.exp(flux_array)),max(np.exp(flux_array))])
example.savefig(outpng)
