#!/usr/bin/env python

# Correcting the declination dependent flux scale of the mosaics for GLEAM. 
# This code will calculate the ratio of flux density from SEDs of bright sources and the 
# measured flux density from Aegean. All sources have a VLSSr counterpart.
# It will then calculate the best fitting polynomial.
# Note that this should be run from directory structure that is above saving directories.
# NHW 17/06/2015

import numpy as np
from astropy.io import fits
from optparse import OptionParser
#from scipy.optimize import curve_fit
from matplotlib import gridspec
#from scipy.stats import gaussian_kde
from scipy.stats import lognorm
from astropy.modeling import models, fitting
import os
import sys

print "#----------------------------------------------------------#"
print '''Fixing final week-long flux scale in GLEAM mosaic. Ensure you have votables from Aegean. 
You need to already run the source finder Aegean on the mosiac and have *_comp.vot and *_isle.vot 
in your working directory. You get the *_isle.vot table from using the --island option in Aegean.
Also ensure that the file marco_all_VLSSsrcs.fits is in $MWA_CODE_BASE. You also need stilts installed on your computer.'''

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('--mosaic',type="string", dest="mosaic",
                    help="The filename of the mosaic you want to read in.")
parser.add_option('--catalog',type="string", dest="catalog",
                    help="The filename of the catalog you want to read in.")
parser.add_option('--isles',type="string", dest="isles",
                    help="The filename of the Aegean islands catalog you want to read in.")
parser.add_option('--plot',action="store_true",dest="make_plots",default=False,
                    help="Make fit plots? (default = False)")
parser.add_option('--write',action="store_true",dest="write_coefficients",default=False,
                    help="Write coefficients to file? (default = False)")
parser.add_option('--table',action="store_true",dest="write_table",default=False,
                    help="Write table used for fit to file? (default = False)")
(options, args) = parser.parse_args()

if options.make_plots:
    import matplotlib as mpl 
    mpl.use('Agg') # So does not use display
    import matplotlib.pyplot as pyplot

def hist_norm_height(n,bins,const):
    ''' Function to normalise bin height by a constant. 
        Needs n and bins from np.histogram.'''

    n = np.repeat(n,2)
    n = np.float32(n) / const
    new_bins = [bins[0]]
    new_bins.extend(np.repeat(bins[1:],2))
    
    return n,new_bins[:-1]

input_mosaic = options.mosaic

dec_zenith=-26.7

#def quad_curvefit_zenith(dec, c, a): # defining quadratic which turns over at the zenith
#    return c*(np.power(dec,2) + dec_zenith*2*dec) + a
def quad_curvefit_zenith(dec, c, a): # defining quadratic which turns over at the zenith
    return c*np.power((dec-dec_zenith),2) + a

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
# Estimating the RA and Dec cuts based on the Week
week=input_root.split("_")[0]

if week == "Week1":
    RA_min = 315
    RA_max = 60
elif week == "Week2":
    RA_min = 0
    RA_max = 70
elif week == "Week3":
    RA_min = 140
    RA_max = 200
elif week == "Week4":
    RA_min = 200
    RA_max = 280
elif week == "Week5":
    RA_min = 330
    RA_max = 360
Dec_min = -30
Dec_max = 30
ylims=(0.5,1.5)
xlims=(Dec_min,Dec_max)
figsize=(5,5)

# Checking if the crossmatch already exists. If it does, skip to the polynomial fitting.
marco_xmatch="marco_all_VLSSsrcs+"+input_root+".fits"

if not os.path.exists(marco_xmatch):

    print "#----------------------------------------------------------#"
    print 'Crossmatching mosaic with literature using stilts.'

    os.system('stilts tmatch2 in1='+options.catalog+' in2='+options.isles+' join=1and2 find=best matcher=exact values1="island" values2="island" out='+input_root+'_tot.vot')
    os.system('stilts tmatch2 matcher=skyellipse in1=$MWA_CODE_BASE/MWA_Tools/catalogues/marco_all_VLSSsrcs.fits in2='+input_root+'_tot.vot out=marco_all_VLSSsrcs+'+input_root+'.fits values1="RAJ2000 DEJ2000 MajAxis MinAxis PA" values2="ra_1 dec_1 a b pa_1" params=20')

hdulist = fits.open(marco_xmatch)
hdulist.verify('fix')
tbdata = hdulist[1].data
hdulist.close()

#week=input_root.split("_")[1][0:8]
#if Dec_strip == -40. or Dec_strip == -55. or Dec_strip == -72. or ( week != "20131107" and week != "20131111" and week != "20131125" and week != "20130822" ):
#    print "Will automatically use corrections from another mosaic."
#    sys.exit(0)

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
# We should avoid sources outside the Dec ranges we're not interested in
indices=np.intersect1d(np.where(tbdata['DEJ2000_vlss']<Dec_max),indices)
indices=np.intersect1d(np.where(tbdata['DEJ2000_vlss']>Dec_min),indices)
if RA_min > RA_max:
# i.e. we're crossing RA 0
   before_meridian=np.intersect1d(np.where(tbdata['RAJ2000_vlss']>RA_min),np.where(tbdata['RAJ2000_vlss']<360.0))
   after_meridian=np.intersect1d(np.where(tbdata['RAJ2000_vlss']>0.0),np.where(tbdata['RAJ2000_vlss']<RA_max))
   indices=np.intersect1d(np.concatenate((before_meridian,after_meridian)),indices)
else:
   indices=np.intersect1d(np.where(tbdata['RAJ2000_vlss']<RA_max),indices)
   indices=np.intersect1d(np.where(tbdata['RAJ2000_vlss']>RA_min),indices)

# All sources which have an MRC match get three data points fitted
indices_mrc=np.intersect1d(np.where(np.bitwise_not(np.isnan(tbdata['S_mrc']))),indices)
freq_array = np.log(np.array([74., 408., 1400.]))
catalogue_fluxes = np.transpose(np.log(np.vstack((tbdata['S_vlss'][indices_mrc],tbdata['S_mrc'][indices_mrc],tbdata['S'][indices_mrc]))))
catalogue_flux_errs = np.transpose(np.vstack((tbdata['e_S_vlss'][indices_mrc],tbdata['e_S_mrc'][indices_mrc],tbdata['e_S'][indices_mrc]))/(np.vstack((tbdata['S_vlss'][indices_mrc],tbdata['S_mrc'][indices_mrc],tbdata['S'][indices_mrc]))))
weights = 1/(catalogue_flux_errs**2)
pred_fluxes=np.empty(catalogue_fluxes.shape[0])
residuals=np.empty(catalogue_fluxes.shape[0])
alpha_mrc=np.empty(catalogue_fluxes.shape[0])
# Currently the vectorized version doesn't care about weights, so we'll have to do this with a loop
#    fit=np.polynomial.polynomial.polyfit(freq_array,catalogue_fluxes,1)

for i in range(0,catalogue_fluxes.shape[0]):
    P,res,rank,singular_values,rcond=np.polyfit(freq_array,catalogue_fluxes[i],1,w=weights[i],full=True)
#        fit[i]=[P[0],P[1],residuals[0]]
    pred_fluxes[i]=powlaw(freq_obs,np.exp(P[1]),P[0])
    residuals[i]=res[0]
    alpha_mrc[i]=P[0]
ratio_mrc=np.log(pred_fluxes/tbdata['int_flux_1'][indices_mrc])
decs_mrc=tbdata['DEJ2000_vlss'][indices_mrc]
ras_mrc=tbdata['RAJ2000_vlss'][indices_mrc]
# Base the weighting entirely off the GLEAM S/N as I do for the XX:YY fits
w_mrc=tbdata['int_flux_1'][indices_mrc]/tbdata['local_rms_1'][indices_mrc]
# Exclude any sources with a crazy high ratio
good_indices=np.where(ratio_mrc<np.log(1.5))
ratio_mrc=ratio_mrc[good_indices]
decs_mrc=decs_mrc[good_indices]
ras_mrc=ras_mrc[good_indices]
w_mrc=w_mrc[good_indices]

# Exclude any sources with a crazy low ratio
good_indices=np.where(ratio_mrc>np.log(0.5))
ratio_mrc=ratio_mrc[good_indices]
decs_mrc=decs_mrc[good_indices]
ras_mrc=ras_mrc[good_indices]
w_mrc=w_mrc[good_indices]

# Sources which lie above Dec+20 only get two data points fitted
freq_array = np.log(np.array([74., 1400.]))
indices_highdec=np.intersect1d(np.where(tbdata['DEJ2000_vlss']>18),indices)

if indices_highdec.any():
    catalogue_fluxes = np.transpose(np.log(np.vstack((tbdata['S_vlss'][indices_highdec],tbdata['S'][indices_highdec]))))
    catalogue_flux_errs = np.transpose(np.vstack((tbdata['e_S_vlss'][indices_highdec],tbdata['e_S'][indices_highdec]))/(np.vstack((tbdata['S_vlss'][indices_highdec],tbdata['S'][indices_highdec]))))
    pred_fluxes=np.empty(catalogue_fluxes.shape[0])
    alpha_highdec=np.empty(catalogue_fluxes.shape[0])

    for i in range(0,catalogue_fluxes.shape[0]):
        P=np.polyfit(freq_array,catalogue_fluxes[i],1)
        pred_fluxes[i]=powlaw(freq_obs,np.exp(P[1]),P[0])
        alpha_highdec[i]=P[0]

    ratio_highdec=np.log(pred_fluxes/tbdata['int_flux_1'][indices_highdec])
    decs_highdec=tbdata['DEJ2000_vlss'][indices_highdec]
    ras_highdec=tbdata['RAJ2000_vlss'][indices_highdec]
    w_highdec=tbdata['int_flux_1'][indices_highdec]/tbdata['local_rms_1'][indices_highdec]
    # Exclude any sources with a crazy high ratio
    good_indices=np.where(ratio_highdec<np.log(1.5))
    ratio_highdec=ratio_highdec[good_indices]
    decs_highdec=decs_highdec[good_indices]
    ras_highdec=ras_highdec[good_indices]
    w_highdec=w_highdec[good_indices]

    # Exclude any sources with a crazy low ratio
    good_indices=np.where(ratio_highdec>np.log(0.5))
    ratio_highdec=ratio_highdec[good_indices]
    decs_highdec=decs_highdec[good_indices]
    ras_highdec=ras_highdec[good_indices]
    w_highdec=w_highdec[good_indices]

    # scipy curve_fit ONLY understands numpy float32s and will fail silently with normal arrays
    alpha=np.array(np.concatenate((alpha_mrc,alpha_highdec),axis=0),dtype="float32")
    ras=np.array(np.concatenate((ras_mrc,ras_highdec),axis=0),dtype="float32")
    x=np.array(np.concatenate((decs_mrc,decs_highdec),axis=0),dtype="float32")
    y=np.array(np.concatenate((ratio_mrc,ratio_highdec),axis=0),dtype="float32")
    w=np.array(np.concatenate((w_mrc,w_highdec),axis=0),dtype="float32")

else:
# If there are no high-dec points, then we want to cut off at Dec 2, because the high-frequency data in week 1 only extends that far north
    good_indices=np.where(decs_mrc<2)
    ratio_mrc=ratio_mrc[good_indices]
    decs_mrc=decs_mrc[good_indices]
    ras_mrc=ras_mrc[good_indices]
    w_mrc=w_mrc[good_indices]
    x=decs_mrc
    y=ratio_mrc
    w=w_mrc
    alpha=alpha_mrc
    ras=ras_mrc

# Straight-line (zeroth order) fit
#polycoeffs=np.polyfit(x,y,0,w=w)
# Don't fit the high Decs because they're not representative of a swarp error
polycoeffs=np.polyfit(decs_mrc,ratio_mrc,0,w=np.log(w_mrc))
print polycoeffs
if indices_highdec.any():
    polycoeffs_highdec=np.polyfit(decs_highdec,ratio_highdec,0,w=np.log(w_highdec))
    print polycoeffs_highdec

if options.write_coefficients:
    outcoeff=input_root+'_fluxscale.fits'
    print "#----------------------------------------------------------#"
    print 'Saving correction to '+outcoeff

    fit_name = ['zero']
    col1 = fits.Column(name='a', format = 'E', array = [polycoeffs[0]])
    cols = fits.ColDefs([col1])
    tbhdu = fits.new_table(cols)
    tbhdu.writeto(outcoeff, clobber = True)

if options.write_table:
    outcoeff=input_root+'_xmatch_table.fits'
    print "#----------------------------------------------------------#"
    print 'Saving crossmatch data to '+outcoeff

    fit_name = ['xmatch_data']
    col1 = fits.Column(name='x', format = 'E', array = x)
    col2 = fits.Column(name='y', format = 'E', array = y)
    col3 = fits.Column(name='w', format = 'E', array = w)
    col4 = fits.Column(name='alpha', format = 'E', array = alpha)
    col5 = fits.Column(name='ras', format = 'E', array = ras)
    cols = fits.ColDefs([col1, col2, col3, col4, col5])
    tbhdu = fits.new_table(cols)
    tbhdu.writeto(outcoeff, clobber = True)

if options.make_plots:
    gs = gridspec.GridSpec(20,30) 
    gs.update(hspace=0,wspace=0)
    outpng=input_root+"_"+"zerofit_int.png"
    title=input_root.split('_')[0]+" "+input_root.split('_')[1]
# Re-sort by S/N so that high S/N points are plotted over the top of low S/N points
    x=[X for (W,X) in sorted(zip(w,x))]
    y=[Y for (W,Y) in sorted(zip(w,y))]
    w=sorted(w)
    SNR=np.log10(w)
    fitmodel = np.poly1d(polycoeffs)
    fitplot=pyplot.figure(figsize=figsize)
#    ax = fitplot.add_subplot(111)
    ax1=pyplot.subplot(gs[0:20,0:20])
    ax1.set_xlim(xlims)
    ax1.set_ylim(ylims)
    ax1.set_xlabel("Dec / degrees")
    ax1.set_ylabel("S_predicted / S_GLEAM")
    ax1.set_title(title,fontsize=10)
    ax1.scatter(x,np.exp(y),marker='+',c=SNR,cmap=pyplot.cm.Greys)
    ax1.plot(np.arange(min(x),max(x),0.01),np.exp(fitmodel(np.arange(min(x),max(x),0.01))),'.',ms=1)
    if indices_highdec.any():
        fitmodel_highdec = np.poly1d(polycoeffs_highdec)
        ax1.plot(np.arange(min(x),max(x),0.01),np.exp(fitmodel_highdec(np.arange(min(x),max(x),0.01))),'.',ms=1)

# Create histograms -- in log space
    ax2=pyplot.subplot(gs[0:20,20:30])
    ax2.set_ylim(ylims)

    ymin=min(y)
    ymax=max(y)
    ny, binsy = np.histogram(y,bins=50,range=(ymin,ymax),weights=w)
# Overall
#    ymin=min(np.exp(y))
#    ymax=max(np.exp(y))
#    ny, binsy = np.histogram(np.exp(y), bins = 50,range=(ymin,ymax),weights = w)
    ny, binsy = hist_norm_height(ny,binsy,ny.max())
    g_init = models.Gaussian1D(amplitude=1., mean=0., stddev=0.1)
    fit_g = fitting.LevMarLSQFitter()
    gy = fit_g(g_init, binsy, ny)
    print np.exp(gy.mean.value)
    print gy.stddev.value
    yrange=np.linspace(ylims[0],ylims[1],1000)
    dist=lognorm(gy.stddev.value,loc=gy.mean.value)
    ax2.plot(dist.pdf(yrange)/max(dist.pdf(yrange)),yrange, 'r-', lw=2, label='Gaussian')

    if indices_highdec.any():
# high-dec
        hmin=min(ratio_highdec)
        hmax=max(ratio_highdec)
        nh, binsh = np.histogram(ratio_highdec, bins = 50,range=(hmin,hmax),weights = w_highdec)
        nh, binsh = hist_norm_height(nh,binsh,nh.max())
        g_init = models.Gaussian1D(amplitude=1., mean=0., stddev=0.1)
        fit_g = fitting.LevMarLSQFitter()
        gh = fit_g(g_init, binsh, nh)
        print np.exp(gh.mean.value)
        print gh.stddev.value
        dist=lognorm(gh.stddev.value,loc=gh.mean.value)
#        ax2.plot(np.exp(gh(hrange)/max(gh(hrange))),hrange, 'g--', lw=2, label='Gaussian')
        ax2.plot(dist.pdf(yrange)/max(dist.pdf(yrange)),yrange, 'g--', lw=2, label='Gaussian')

# MRC
    mmin=min(ratio_mrc)
    mmax=max(ratio_mrc)
    nm, binsm = np.histogram(ratio_mrc, bins = 50,range=(mmin,mmax),weights = w_mrc)
    nm, binsm = hist_norm_height(nm,binsm,nm.max())
    g_init = models.Gaussian1D(amplitude=1., mean=0., stddev=0.1)
    fit_g = fitting.LevMarLSQFitter()
    gm = fit_g(g_init, binsm, nm)
    print gm.mean.value
    print np.exp(gm.mean.value)
    print gm.stddev.value
    dist=lognorm(gm.stddev.value,loc=gm.mean.value)
    ax2.plot(dist.pdf(yrange)/max(dist.pdf(yrange)),yrange, 'b--', lw=2, label='Gaussian')
    # Stdev trace
#    ax2.plot([0,gy(gy.mean.value-gy.stddev.value)],[gy.mean.value-gy.stddev.value,gy.mean.value-gy.stddev.value], 'k--', lw=1)
#    ax2.plot([0,gy(gy.mean.value+gy.stddev.value)],[gy.mean.value+gy.stddev.value,gy.mean.value+gy.stddev.value], 'k--', lw=1)
    ax2.set_xticklabels([])
    ax2.set_yticklabels([])
    fitplot.savefig(outpng,pad_inches=0.0,bbox_inches='tight')
