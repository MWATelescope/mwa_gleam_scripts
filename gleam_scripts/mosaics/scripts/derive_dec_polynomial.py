#!/usr/bin/env python

# Correcting the declination dependent flux scale of the mosaics for GLEAM. 
# This code will calculate the ratio of flux density from SEDs of bright sources and the 
# measured flux density from Aegean. All sources have a VLSSr counterpart.
# It will then calculate the best fitting polynomial.
# Note that this should be run from directory structure that is above saving directories.
# J. R. Callingham 26/2/2015

import datetime
import numpy as np
import scipy.optimize as opt
import scipy.stats as stats
from astropy.io import fits
from optparse import OptionParser
import os
import sys

print "#----------------------------------------------------------#"
print '''Fixing declination dependent flux scale in GLEAM mosaic. Ensure you have votables from Aegean. 
You need to already run the source finder Aegean on the mosiac and have *_comp.vot and *_isle.vot 
in your working directory. You get the *_isle.vot table from using the --island option in Aegean.
Also ensure that the file marco_all_VLSSsrcs.fits is in $MWA_CODE_BASE. You also need stilts installed on your computer.'''

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('--mosaic',type="string", dest="mosaic",
                    help="The filename of the mosaic you want to read in.")
parser.add_option('--plot',action="store_true",dest="make_plots",default=True,
                    help="Make fit plots? (default = True)")
parser.add_option('--zenith',action="store_true",dest="zenith",default=False,
                    help="Calculate correction for the special case of zenith.")
(options, args) = parser.parse_args()

if options.make_plots:
    import matplotlib as mpl 
    mpl.use('Agg') # So does not use display
    import matplotlib.pyplot as pyplot

    sbplt_pad_left  = 0.125  # the left side of the subplots of the figure
    sbplt_pad_right = 0.9    # the right side of the subplots of the figure
    sbplt_pad_bottom = 0.1   # the bottom of the subplots of the figure
    sbplt_pad_top = 0.9      # the top of the subplots of the figure
    sbplt_pad_wspace = 0.2   # the amount of width reserved for blank space between subplots
    sbplt_pad_hspace = 0.5   # the amount of height reserved for white space between subplots

    figsize=(5,5)

input_mosaic = options.mosaic

def powlaw(freq, a, alpha): # defining powlaw as S = a*nu^alpha.
    return a*(freq**alpha)

input_root=input_mosaic.replace(".fits","")

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

# Reading in the RA and Dec cuts from the limits file

cutdir=os.environ['MWA_CODE_BASE']

centre_dec, freq_band, RA_min, RA_max, Dec_min, Dec_max = np.loadtxt(cutdir+'/MWA_Tools/gleam_scripts/mosaics/ra_dec_limits_polyderivation.dat',skiprows=2,unpack=True) 

dec_freq_comb = [centre_dec, freq_band]
cut_ind = np.where((centre_dec == Dec_strip) & (freq_band == subband))
RA_min = RA_min[cut_ind]
RA_max = RA_max[cut_ind]
Dec_min = Dec_min[cut_ind]
Dec_max = Dec_max[cut_ind]

# Checking if file with ratios already exists. If it does, skip to straight fitting. 
marco_xmatch="marco_all_VLSSsrcs+"+input_root+".fits"

if not os.path.exists(marco_xmatch):

    print "#----------------------------------------------------------#"
    print 'Crossmatching mosaic with literature using stilts.'

    os.system('stilts tmatch2 in1='+input_root+'_comp.vot in2='+input_root+'_isle.vot join=1and2 find=best matcher=exact values1="island" values2="island" out='+input_root+'_tot.vot')
    os.system('stilts tmatch2 matcher=skyellipse in1=$MWA_CODE_BASE/MWA_Tools/catalogues/marco_all_VLSSsrcs.fits in2='+input_root+'_tot.vot out=marco_all_VLSSsrcs+'+input_root+'.fits values1="RAJ2000 DEJ2000 MajAxis MinAxis PA" values2="ra_1 dec_1 a b pa_1" params=20')

hdulist = fits.open(marco_xmatch)
hdulist.verify('fix')
tbdata = hdulist[1].data
hdulist.close()

week=input_root.split("_")[1][0:8]
if Dec_strip == -40. or Dec_strip == -55. or Dec_strip == -72. or ( week != "20131107" and week != "20131111" and week != "20131125" and week != "20130822" ):
    print "Will automatically use corrections from another mosaic."
    sys.exit(0)

print "#----------------------------------------------------------#"
print 'Analysing '+input_mosaic

# Aegean flags should be OK
indices=np.concatenate((np.where(tbdata['flags_1'] & 101)[0],np.where(tbdata['flags_1'] == 0)[0]))
# We want them to be isolated
indices=np.intersect1d(np.where(tbdata['isolated']==True),indices)
# Should only have a single component in the fit
indices=np.intersect1d(np.where(tbdata['components']==1),indices)
# Flux in VLSS should be more than 2Jy
indices=np.intersect1d(np.where(tbdata['S_vlss']>2.),indices)
# Sources should be more than 8 sigma in GLEAM
indices=np.intersect1d(np.where((tbdata['int_flux_1']/tbdata['local_rms_1'])>8),indices)
# We should avoid sources outside the RA and Dec ranges we're not interested in (currently manually set, need to read from a file)
indices=np.intersect1d(np.where(tbdata['DEJ2000_vlss']<Dec_max),indices)
indices=np.intersect1d(np.where(tbdata['DEJ2000_vlss']>Dec_min),indices)
if RA_min > RA_max:
# i.e. we're crossing RA 0
   before_meridian=np.intersect1d(np.where(tbdata['RAJ2000_vlss']>RA_min),np.where(np.where(tbdata['RAJ2000_vlss']<360.0)))
   after_meridian=np.intersect1d(np.where(tbdata['RAJ2000_vlss']>0.0),np.where(np.where(tbdata['RAJ2000_vlss']<RA_max)))
   indices=np.intersect1d(np.concatenate(before_meridian,after_meridian),indices)
else:
   indices=np.intersect1d(np.where(tbdata['DEJ2000_vlss']<RA_max),indices)
   indices=np.intersect1d(np.where(tbdata['DEJ2000_vlss']>RA_min),indices)

# All sources which have an MRC match get three data points fitted
indices_mrc=np.intersect1d(np.where(np.bitwise_not(np.isnan(tbdata['S_mrc']))),indices)
freq_array = np.log(np.array([74., 408., 1400.]))
catalogue_fluxes = np.transpose(np.log(np.vstack((tbdata['S_vlss'][indices_mrc],tbdata['S_mrc'][indices_mrc],tbdata['S'][indices_mrc]))))
catalogue_flux_errs = np.transpose(np.vstack((tbdata['e_S_vlss'][indices_mrc],tbdata['e_S_mrc'][indices_mrc],tbdata['e_S'][indices_mrc]))/(np.vstack((tbdata['S_vlss'][indices_mrc],tbdata['S_mrc'][indices_mrc],tbdata['S'][indices_mrc]))))
weights = 1/(catalogue_flux_errs**2)
#    fit=np.empty((weights.shape[0],3))
pred_fluxes=np.empty(catalogue_fluxes.shape[0])
residuals=np.empty(catalogue_fluxes.shape[0])
# Currently the vectorized version doesn't care about weights, so we'll have to do this with a loop
#    fit=np.polynomial.polynomial.polyfit(freq_array,catalogue_fluxes,1)

for i in range(0,catalogue_fluxes.shape[0]):
    P,res,rank,singular_values,rcond=np.polyfit(freq_array,catalogue_fluxes[i],1,w=weights[i],full=True)
#        fit[i]=[P[0],P[1],residuals[0]]
    pred_fluxes[i]=powlaw(freq_obs,np.exp(P[1]),P[0])
    residuals[i]=res[0]
ratio=np.log(pred_fluxes/tbdata['int_flux_1'][indices_mrc])
decs=tbdata['DEJ2000_vlss'][indices_mrc]
# Base the weighting entirely off the GLEAM S/N as I do for the XX:YY fits
w=tbdata['int_flux_1'][indices_mrc]/tbdata['local_rms_1'][indices_mrc]

#plot_weights=(1/residuals)*1e4

# Sources which lie above Dec+20 only get two data points fitted
freq_array = np.log(np.array([74., 1400.]))
indices_highdec=np.intersect1d(np.where(tbdata['DEJ2000_vlss']>18),indices)
catalogue_fluxes = np.transpose(np.log(np.vstack((tbdata['S_vlss'][indices_highdec],tbdata['S'][indices_highdec]))))
catalogue_flux_errs = np.transpose(np.vstack((tbdata['e_S_vlss'][indices_highdec],tbdata['e_S'][indices_highdec]))/(np.vstack((tbdata['S_vlss'][indices_highdec],tbdata['S'][indices_highdec]))))
pred_fluxes=np.empty(catalogue_fluxes.shape[0])

for i in range(0,catalogue_fluxes.shape[0]):
    P=np.polyfit(freq_array,catalogue_fluxes[i],1)
    pred_fluxes[i]=powlaw(freq_obs,np.exp(P[1]),P[0])

ratio2=np.log(pred_fluxes/tbdata['int_flux_1'][indices_highdec])
decs2=tbdata['DEJ2000_vlss'][indices_highdec]
w2=tbdata['int_flux_1'][indices_highdec]/tbdata['local_rms_1'][indices_highdec]
#plot_weights2=np.ones(catalogue_fluxes.shape[0])

x=np.concatenate((decs,decs2),axis=1)
y=np.concatenate((ratio,ratio2),axis=1)
w=np.concatenate((w,w2),axis=1)

polycoeffs=np.polyfit(x,y,3,w=w)

if options.make_plots:
    outpng=input_root+"_"+"polyfit_int.png"
    title=input_root.split('_')[1]+' Dec '+str(Dec_strip)+' '+input_root.split('_')[2]
# Re-sort by S/N so that high S/N points are plotted over the top of low S/N points
    x=[X for (W,X) in sorted(zip(w,x))]
    y=[Y for (W,Y) in sorted(zip(w,y))]
    w=sorted(w)
    SNR=np.log10(w)
    fitmodel = np.poly1d(polycoeffs)
    fitplot=pyplot.figure(figsize=figsize)
    ax = fitplot.add_subplot(111)
    ax.set_xlim(min(x),max(x))
    ax.set_xlabel("Dec / degrees")
    ax.set_ylabel("S_predicted / S_GLEAM")
    ax.set_title(title,fontsize=10)
    ax.scatter(x,np.exp(y),marker='+',c=SNR,cmap=pyplot.cm.Greys)
    ax.plot(np.arange(min(x),max(x),0.01),np.exp(fitmodel(np.arange(min(x),max(x),0.01))),'.',ms=1)
    fitplot.savefig(outpng,pad_inches=0.0,bbox_inches='tight')
