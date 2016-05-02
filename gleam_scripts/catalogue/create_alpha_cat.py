#!/usr/bin/env python

# Create a simplified version of the GLEAM catalogue with two fluxes and a spectral index
# And errors
# I print two fluxes so that Andre's tools can easily generate peelable models
# Modified to use PUMA's crossmatched table

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
parser.add_option('--output',type="string", dest="output",
                    help="The filename of the output.", default=None)
#parser.add_option('--plot',action="store_true",dest="make_plots",default=False,
#                  help="Make fit plots? (default = False)")
parser.add_option('--order',dest="poly_order",default=1,type=int,
                  help="Set the order of the polynomial fit. (default = 1)")
(options, args) = parser.parse_args()

# http://scipy-cookbook.readthedocs.org/items/FittingData.html
# Define function for calculating a power law
powerlaw = lambda x, amp, index: amp * (x**index)

# define our (line) fitting function
fitfunc = lambda p, x: p[0] + p[1] * x
errfunc = lambda p, x, y, err: (y - fitfunc(p, x)) / err

if options.output is None:
    output="test.vot"
else:
    output=options.output

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
#freqs=["076", "084", "092", "099", "107",  "115", "122", "130", "143", "151", "158", "166", "174",  "181", "189","197", "204", "212", "220", "227"]
freqs=["76", "84", "92", "99", "107",  "115", "122", "130", "143", "151", "158", "166", "174",  "181", "189","197", "204", "212", "220", "227"]

# Can only fit positive values in log space
#flux_array = np.transpose(np.ma.log([np.ma.masked_less_equal(data["int_flux_"+x],0) for x in freqs]))
flux_array = np.ma.array(np.transpose(np.ma.log([np.ma.masked_less_equal(data["S_"+x],0) for x in freqs])),dtype="float32")
# Error propagation: error on log(x) = err_x/x
#flux_errors = np.transpose(np.ma.array([data["err_int_flux_"+x]/np.ma.masked_less_equal(data["int_flux_"+x],0) for x in freqs]))
flux_errors = np.ma.array(np.transpose(np.ma.array([data["e_S_"+x]/np.ma.masked_less_equal(data["S_"+x],0) for x in freqs])),dtype="float32")
weights = 1/(flux_errors*flux_errors)
# Frequencies
freq_array = np.log(np.ma.array([float(int(x)) for x in freqs]),dtype="float32")

alpha=np.empty(flux_array.shape[0])
err_alpha=np.empty(flux_array.shape[0])
flux1=np.empty(flux_array.shape[0])
err_flux1=np.empty(flux_array.shape[0])
flux2=np.empty(flux_array.shape[0])
err_flux2=np.empty(flux_array.shape[0])
amp=np.empty(flux_array.shape[0])

for i in range(0,flux_array.shape[0]):
    pinit = [-2.0, -0.7]
    fit = leastsq(errfunc, pinit, args=(freq_array, flux_array[i], flux_errors[i]), full_output=1)
# Just checking using numpy's polyfit
#    npP=np.ma.polyfit(freq_array,flux_array[i],options.poly_order,w=1/flux_errors[i])
#    npalpha = npP[0]
#    npamp = np.exp(npP[1])
    covar = fit[1]
    if covar is not None:
        P = fit[0]
        alpha[i]=P[1]
        amp[i] = np.exp(P[0])
        flux1[i]=powerlaw(freq1,amp[i],alpha[i])
        flux2[i]=powerlaw(freq2,amp[i],alpha[i])
    # Errors
        err_alpha[i] = np.sqrt(covar[0][0])
        err_flux1[i] = np.sqrt(covar[1][1])*flux1[i]
        err_flux2[i] = np.sqrt(covar[1][1])*flux2[i]
    else:
        alpha[i]=None
        amp[i]=None
        flux1[i]=None
        flux2[i]=None
        err_alpha[i]=None
        err_flux1[i]=None
        err_flux2[i]=None

indices = np.where(np.bitwise_not(np.isnan(alpha)))

# Generate the output VO table
outtable=Table()
#outtable.add_column(Column(data=data['ra_deep'],name='RAJ2000'))
#outtable.add_column(Column(data=data['dec_deep'],name='DEJ2000'))
outtable.add_column(Column(data=data['updated_RAJ2000'][indices],name='RAJ2000'))
outtable.add_column(Column(data=data['updated_DECJ2000'][indices],name='DEJ2000'))
#outtable.add_column(Column(data=data['local_rms_deep'],name='local_rms_deep'))
#outtable.add_column(Column(data=data['int_flux_deep'],name='int_flux_deep'))
outtable.add_column(Column(data=alpha[indices],name='alpha'))
outtable.add_column(Column(data=err_alpha[indices],name='err_alpha'))
outtable.add_column(Column(data=flux1[indices],name='S_72'))
outtable.add_column(Column(data=err_flux1[indices],name='err_S_72'))
outtable.add_column(Column(data=flux2[indices],name='S_231'))
outtable.add_column(Column(data=err_flux2[indices],name='err_S_231'))

if os.path.exists(output):
    os.remove(output)
outtable.write(output,format='votable')

# Plot last source as an example

example=plt.figure(figsize=(5,10))
ax1=example.add_subplot(2,1,1)
ax1.plot(np.exp(freq_array), powerlaw(np.exp(freq_array), amp[i], alpha[i]))     # Fit
#ax1.plot(np.exp(freq_array), powerlaw(np.exp(freq_array), npamp, npalpha))     # Fit
ax1.errorbar(np.exp(freq_array), np.exp(flux_array[i]), yerr=flux_errors[i]*np.exp(flux_array[i]), fmt='k.')  # Data
ax2=example.add_subplot(2,1,2)
ax2.loglog(np.exp(freq_array), powerlaw(np.exp(freq_array), amp[i], alpha[i]))     # Fit
#ax2.loglog(np.exp(freq_array), powerlaw(np.exp(freq_array), npamp, npalpha))     # Fit
ax2.errorbar(np.exp(freq_array), np.exp(flux_array[i]), yerr=flux_errors[i]*np.exp(flux_array[i]), fmt='k.')  # Data
example.savefig('test.png')
