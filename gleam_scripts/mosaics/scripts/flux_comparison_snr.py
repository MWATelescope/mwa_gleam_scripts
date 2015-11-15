#!/usr/bin/env python

# Checking flux scale of calibrated large mosaics to make sure it is consistent with derivation.

import datetime
import os
import matplotlib
matplotlib.use('Agg')
import numpy as np
import matplotlib.pyplot as plt
import astropy.units as u
from scipy.optimize import curve_fit
from astropy.io import fits
from astropy.coordinates import SkyCoord
from astropy.modeling import models, fitting
from optparse import OptionParser

# Setting font. If this breaks on the supercomputer, just uncomment these two lines.
# from matplotlib import rc
# rc('text', usetex=True)
# rc('font',**{'family':'serif','serif':['serif']})

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('--mosaic',type="string", dest="mosaic",
                    help="The filename of the catalogue you want to read in. Exclude _comp.vot extension.")
parser.add_option('--fitsfile',type="string", dest="fitsfile",
                    help="The filename of the fits file you want to read in. Default = catalogue.fits")
parser.add_option('--peak',action="store_false",dest="int",default=False,
                    help="Use peak flux rather than int flux (default = False)")
parser.add_option('--printaverage',action="store_true",dest="printaverage",default=False,
                    help="Print the average flux ratio correction (default = False)")
(options, args) = parser.parse_args()

input_mosaic = options.mosaic

print 'Before '+input_mosaic+': '+str(datetime.datetime.now())

# Checking if fluxdentable exists

if options.int:
    suffix="int"
    check_file = os.path.exists(input_mosaic+'_fluxdentable_'+suffix+'.fits')
else:
    suffix="peak"
    check_file = os.path.exists(input_mosaic+'_fluxdentable_'+suffix+'.fits')

# if not check_file:

    # Getting freq.
if options.fitsfile:
    fitsfile=options.fitsfile
else:
    fitsfile=input_mosaic+'.fits'
header = fits.getheader(fitsfile)
try:
    freq_obs = header['CRVAL3']/1e6
except:
    freq_obs = header['FREQ']/1e6

def redchisq(ydata,ymod,sd,deg):
    chisq=np.sum(((ydata-ymod)/sd)**2)
    nu=ydata.size-1-deg
    return [chisq, chisq/nu]#, chisq/nu

def powlaw(freq, a, alpha): # defining powlaw as S = a*nu^alpha.
    return a*(freq**alpha)

os.system('stilts tmatch2 matcher=skyellipse in1=$MWA_CODE_BASE/marco_all_VLSSsrcs.fits in2='+input_mosaic+'_comp.vot out=marco_all_VLSSsrcs+'+input_mosaic+'.fits values1="RAJ2000 DEJ2000 MajAxis MinAxis PA" values2="ra dec a b pa" params=20')
# os.system('stilts tmatch2 matcher=skyellipse in1=/Users/jcal/scripts/python/MWA_Tools/catalogues/marco_all_VLSSsrcs.fits in2='+input_mosaic+'_comp.vot out=marco_all_VLSSsrcs+'+input_mosaic+'.fits values1="RAJ2000 DEJ2000 MajAxis MinAxis PA" values2="ra dec a b pa" params=20')

hdulist = fits.open('marco_all_VLSSsrcs+'+input_mosaic+'.fits')
hdulist.verify('fix')
tbdata = hdulist[1].data
hdulist.close()

def filter_GalacticPlane(table):
    """
    Filter out sources that have |b|<10\deg, consistent with the SUMSS/MGPS-2 division
    """

    print "Filtering Galactic plane"
    bmax = 10
    good = []
    b = abs(SkyCoord(table['RAJ2000']*u.deg, table['DEJ2000']*u.deg,frame="icrs").galactic.b.degree)
    good = np.where(b>=bmax)
    return  table[good]

tbdata = filter_GalacticPlane(tbdata)

indices=np.concatenate((np.where(tbdata['flags'] & 101)[0],np.where(tbdata['flags'] == 0)[0]))
# We want them to be isolated
indices=np.intersect1d(np.where(tbdata['isolated']==True),indices)
# Should only have a single component in the fit
# indices=np.intersect1d(np.where(tbdata['components']==1),indices)
# Flux in VLSS should be more than 2Jy
indices=np.intersect1d(np.where(tbdata['S_vlss']>2.),indices)
if suffix == 'int':
    # Sources should be more than 8 sigma in GLEAM
    indices=np.intersect1d(np.where((tbdata['int_flux']/tbdata['local_rms'])>8),indices)
else:
    indices=np.intersect1d(np.where((tbdata['peak_flux']/tbdata['local_rms'])>8),indices)

# All sources which have an MRC match get three data points fitted
indices_mrc=np.intersect1d(np.where(np.bitwise_not(np.isnan(tbdata['S_mrc']))),indices)
freq_array = np.log(np.array([74., 408., 1400.]))
catalogue_fluxes = np.transpose(np.log(np.vstack((tbdata['S_vlss'][indices_mrc],tbdata['S_mrc'][indices_mrc],tbdata['S'][indices_mrc]))))
# catalogue_flux_errs = np.transpose(np.vstack((tbdata['e_S_vlss'][indices_mrc],tbdata['e_S_mrc'][indices_mrc],tbdata['e_S'][indices_mrc]))/(np.vstack((tbdata['S_vlss'][indices_mrc],tbdata['S_mrc'][indices_mrc],tbdata['S'][indices_mrc]))))
catalogue_flux_errs = np.transpose(np.vstack((np.sqrt((tbdata['e_S_vlss'][indices_mrc])**2 + (np.exp(tbdata['e_S_vlss'][indices_mrc])*0.1)**2),tbdata['e_S_mrc'][indices_mrc],tbdata['e_S'][indices_mrc]))/(np.vstack((tbdata['S_vlss'][indices_mrc],tbdata['S_mrc'][indices_mrc],tbdata['S'][indices_mrc])))) # fixing problem with VLSSr uncertainties here too.
# catalogue_flux_errs = np.transpose(np.vstack((tbdata['e_S_vlss'][indices_mrc],tbdata['e_S_mrc'][indices_mrc],tbdata['e_S'][indices_mrc])))
# catalogue_flux_errs[:,0] = np.sqrt((catalogue_flux_errs[:,0])**2 + (np.exp(catalogue_fluxes[:,0])*0.1)**2) # fixing problem with VLSSr uncertainties

weights = 1/(catalogue_flux_errs**2)
pred_fluxes=np.empty(catalogue_fluxes.shape[0])
residuals=np.empty(catalogue_fluxes.shape[0])
redchisq_val=np.empty(catalogue_fluxes.shape[0])
specind = np.empty(catalogue_fluxes.shape[0])
Name = tbdata['ID'][indices_mrc]
p0pow = [-0.7,1]
# Currently the vectorized version doesn't care about weights, so we'll have to do this with a loop
#    fit=np.polynomial.polynomial.polyfit(freq_array,catalogue_fluxes,1)

for i in range(0,catalogue_fluxes.shape[0]):
    P,res,rank,singular_values,rcond=np.polyfit(freq_array,catalogue_fluxes[i],1,w=weights[i],full=True)
    poptpowlaw, pcovpowlaw = curve_fit(powlaw, np.exp(freq_array), np.exp(catalogue_fluxes[i]), p0 = p0pow, sigma = catalogue_flux_errs[i], maxfev = 10000)
    # pred_fluxes[i]=powlaw(freq_obs,*poptpowlaw)
    pred_fluxes[i]=powlaw(freq_obs,np.exp(P[1]),P[0])
    specind[i] = P[0]#poptpowlaw[1]
    fit_spec = np.poly1d(P)
    redchisq_val[i] = redchisq(catalogue_fluxes[i],fit_spec(freq_array),catalogue_flux_errs[i],2)[0]
    # redchisq_val[i] = redchisq(np.exp(catalogue_fluxes[i]),powlaw(np.exp(freq_array),*poptpowlaw),catalogue_flux_errs[i],2)[0]
    residuals[i]=res[0]

if suffix == 'int':
    ratio_mrc=np.log(pred_fluxes/tbdata['int_flux'][indices_mrc])
    # Base the weighting entirely off the GLEAM S/N as I do for the XX:YY fits
    w_mrc=tbdata['int_flux'][indices_mrc]/tbdata['local_rms'][indices_mrc]
else:
    ratio_mrc=np.log(pred_fluxes/tbdata['peak_flux'][indices_mrc])
    # Base the weighting entirely off the GLEAM S/N as I do for the XX:YY fits
    w_mrc=tbdata['peak_flux'][indices_mrc]/tbdata['local_rms'][indices_mrc]
decs_mrc=tbdata['DEJ2000_vlss'][indices_mrc]

# Ensuring the source is well fit by a powerlaw and not flat.
indices_redchisq = np.where((redchisq_val < 15.) & (abs(specind) > 0.5))
ratio_mrc = ratio_mrc[indices_redchisq]
decs_mrc = decs_mrc[indices_redchisq]
w_mrc = w_mrc[indices_redchisq]

freq_array = np.log(np.array([74., 1400.]))
indices_highdec=np.intersect1d(np.where(tbdata['DEJ2000_vlss']>18.5),indices)
catalogue_fluxes = np.transpose(np.log(np.vstack((tbdata['S_vlss'][indices_highdec],tbdata['S'][indices_highdec]))))
# catalogue_flux_errs = np.transpose(np.vstack((tbdata['e_S_vlss'][indices_highdec],tbdata['e_S'][indices_highdec]))/(np.vstack((tbdata['S_vlss'][indices_highdec],tbdata['S'][indices_highdec]))))
catalogue_flux_errs = np.transpose(np.vstack((np.sqrt((tbdata['e_S_vlss'][indices_highdec])**2 + (np.exp(tbdata['e_S_vlss'][indices_highdec])*0.1)**2),tbdata['e_S'][indices_highdec]))/(np.vstack((tbdata['S_vlss'][indices_highdec],tbdata['S'][indices_highdec]))))
# catalogue_flux_errs = np.transpose(np.vstack((tbdata['e_S_vlss'][indices_highdec],tbdata['e_S'][indices_highdec])))

pred_fluxes=np.empty(catalogue_fluxes.shape[0])
redchisq_val=np.empty(catalogue_fluxes.shape[0])
specind = np.empty(catalogue_fluxes.shape[0])
Name = tbdata['ID'][indices_highdec]

for i in range(0,catalogue_fluxes.shape[0]):
    P=np.polyfit(freq_array,catalogue_fluxes[i],1)
    poptpowlaw, pcovpowlaw = curve_fit(powlaw, np.exp(freq_array), np.exp(catalogue_fluxes[i]), p0 = p0pow, sigma = catalogue_flux_errs[i], maxfev = 10000)
    pred_fluxes[i]=powlaw(freq_obs,np.exp(P[1]),P[0])
    # pred_fluxes[i]=powlaw(freq_obs,*poptpowlaw)
    specind[i] = P[0]#poptpowlaw[1]
    fit_spec = np.poly1d(P)
    redchisq_val[i] = redchisq(catalogue_fluxes[i],fit_spec(freq_array),catalogue_flux_errs[i],2)[0]
    # redchisq_val[i] = redchisq(np.exp(catalogue_fluxes[i]),powlaw(np.exp(freq_array),*poptpowlaw),catalogue_flux_errs[i],2)[0]

if suffix == 'int':
    ratio_highdec=np.log(pred_fluxes/tbdata['int_flux'][indices_highdec])
    # Base the weighting entirely off the GLEAM S/N as I do for the XX:YY fits
    w_highdec=tbdata['int_flux'][indices_highdec]/tbdata['local_rms'][indices_highdec]
else:
    ratio_highdec=np.log(pred_fluxes/tbdata['peak_flux'][indices_highdec])
    # Base the weighting entirely off the GLEAM S/N as I do for the XX:YY fits
    w_highdec=tbdata['peak_flux'][indices_highdec]/tbdata['local_rms'][indices_highdec]

decs_highdec=tbdata['DEJ2000_vlss'][indices_highdec]

# Ensuring the source is well fit by a powelaw and not flat.
indices_redchisq_highdec = np.where((redchisq_val < 10.) & (abs(specind) > 0.5))
ratio_highdec = ratio_highdec[indices_redchisq_highdec]
decs_highdec = decs_highdec[indices_redchisq_highdec]
w_highdec = w_highdec[indices_redchisq_highdec]

# scipy curve_fit ONLY understands numpy float32s and will fail silently with normal arrays
x=np.array(np.concatenate((decs_mrc,decs_highdec),axis=1),dtype="float32")
y=np.array(np.concatenate((ratio_mrc,ratio_highdec),axis=1),dtype="float32")
w=np.array(np.concatenate((w_mrc,w_highdec),axis=1),dtype="float32")

def zero_curvefit(dec,a):
    return a

def lin_curvefit(dec, a, b): # defining quadratic
    return b*dec + a

a_fit, b_fit, c_fit, d_fit, e_fit = [np.zeros(2) for t in range(5)] 

p_guess_zero = [ 1.5]
poptzero, pcovzero = curve_fit(zero_curvefit, x, y, p0 = p_guess_zero, sigma = 1/np.sqrt(w), absolute_sigma=False, maxfev = 10000)
a_fit[0] = poptzero[0]

p_guess_lin = [ 1.0,  7e-02]
poptlin, pcovlin = curve_fit(lin_curvefit, x, y, p0 = p_guess_lin, sigma = 1/np.sqrt(w), absolute_sigma=False, maxfev = 10000)
a_fit[1], b_fit[1] = poptlin[0], poptlin[1]

def hist_norm_height(n,bins,const):
    ''' Function to normalise bin height by a constant. 
        Needs n and bins from np.histogram.'''

    n = np.repeat(n,2)
    n = np.float32(n) / const
    new_bins = [bins[0]]
    new_bins.extend(np.repeat(bins[1:],2))
    
    return n,new_bins[:-1]

# Identifying sources above and below dec. 18.5 deg. 

dec18_ind = np.where(x >= 18.5)
ratio_dec18 = np.exp(y[dec18_ind])
ratio_err_dec18 = w[dec18_ind]
dec18_less_ind = np.where(x < 18.5)
ratio_less_dec18 = np.exp(y[dec18_less_ind])
ratio_err_less_dec18 = w[dec18_less_ind]

SNR = np.log10(w)

plt.rcParams['figure.figsize'] = 12, 5 # Setting figure size. Have to close window for it to have effect.
gs = plt.GridSpec(1,2, wspace = 0, width_ratios = [3,1])
ax = plt.subplot(gs[0])
ax1 = plt.subplot(gs[1])
ax.scatter(x, np.exp(y), marker='o', c=SNR, cmap=plt.cm.Greys)#, c=SNR, cmap=plt.cm.Greys)
dec_long = np.arange(min(x)+0.07*min(x),max(x)+0.10*max(x),0.1)
dec_long = np.array(dec_long)
ax.plot(dec_long,np.ones(len(dec_long))*zero_curvefit(dec_long, *np.exp(poptzero)), 'saddlebrown', linewidth = 3, label="All Dec.")
# ax.plot(dec_long,np.ones(len(dec_long))*zero_curvefit(dec_long, *poptzero_ratio_dec18), 'crimson', linewidth = 3, label="Dec. > 18")
# ax.plot(dec_long,np.ones(len(dec_long))*zero_curvefit(dec_long, *poptzero_ratio_less_dec18), 'navy', linewidth = 3, label="Dec. < 18")
ax.legend(loc='upper right', fontsize=10) # make a legend in the best location
ax.tick_params(axis='y', labelsize=15)
ax.tick_params(axis='x', labelsize=15)
ax.set_xlim(min(x)+0.07*min(x), max(x)+0.10*max(x))
y_lim_plot = [0.4,1.6]
ax.set_ylim(y_lim_plot)
ax.set_xlabel('Dec. (degrees)', fontsize = 15)
ax.set_ylabel('Pred. flux density / Obs. flux density', fontsize = 15)
n, bins = np.histogram(np.exp(y), bins = 20,weights = w)
n, bins = hist_norm_height(n,bins,n.max())

# Fitting gaussian to distriution
g_init = models.Gaussian1D(amplitude=1., mean=1., stddev=1.)
fit_g = fitting.LevMarLSQFitter()
g = fit_g(g_init, bins, n)
# g = fit_g(g_init, bins, ratio)

# Plotting histograms
n_dec18, bins_dec18 = np.histogram(ratio_dec18, bins = 20,weights = ratio_err_dec18)
n_dec18, bins_dec18 = hist_norm_height(n_dec18,bins_dec18,n_dec18.max())
n_less_dec18, bins_less_dec18 = np.histogram(ratio_less_dec18, bins = 20,weights = ratio_err_less_dec18)
n_less_dec18, bins_less_dec18 = hist_norm_height(n_less_dec18,bins_less_dec18,n_less_dec18.max())
g_dec18 = fit_g(g_init, bins_dec18, n_dec18)
g_less_dec18 = fit_g(g_init, bins_less_dec18, n_less_dec18)
ax1.step(n, bins, color = 'k',linewidth = 2, label="All Dec.")
ax1.plot(g(np.linspace(y_lim_plot[0],y_lim_plot[1],100)),np.linspace(y_lim_plot[0],y_lim_plot[1],100), 'r-', lw=2, label='All')
ax1.plot(g_dec18(np.linspace(y_lim_plot[0],y_lim_plot[1],100)),np.linspace(y_lim_plot[0],y_lim_plot[1],100), 'b-', lw=2, label='Dec. > 18.5')
ax1.plot(g_less_dec18(np.linspace(y_lim_plot[0],y_lim_plot[1],100)),np.linspace(y_lim_plot[0],y_lim_plot[1],100), 'g-', lw=2, label='Dec. < 18.5')
ax1.step(n_dec18, bins_dec18, color = 'k', linestyle = 'dashed', label="Dec. > 18.5")
ax1.step(n_less_dec18, bins_less_dec18, color = 'k',linestyle = 'dotted', label="Dec. < 18.5")
ax1.legend(loc='upper right', fontsize=10) # make a legend in the best location
ax1.yaxis.set_ticklabels([])   # remove the major ticks
ax1.set_ylim(y_lim_plot)
start_x, end_x = ax1.get_xlim()
start_y, end_y = ax1.get_ylim()
ax1.xaxis.set_ticks([0.5, 1.0])
n_range = np.arange(start_x, end_x,0.01)
ax.set_title(input_mosaic+' Freq = '+str(freq_obs))
ax1.set_title(r'$\mu$ = '+str(round(g.mean[0],4))+r' $\sigma$ = '+str(round(g.stddev[0],4)), fontsize = 10)
ax1.plot(n_range,np.ones(len(n_range))*zero_curvefit(n_range, *np.exp(poptzero)), 'saddlebrown', linewidth = 3)
# ax1.xaxis.set_major_locator(MaxNLocator(prune='lower'))
cb = plt.colorbar(ax.scatter(x, np.exp(y), marker='o',color ='k',c=SNR, cmap=plt.cm.Greys))
cb.set_label('log(SNR)',fontsize = 15)
plt.savefig(input_mosaic+'_'+suffix+'_'+str(freq_obs)+'MHz_flux_fits.png')

# Plotting CDF

plt.rcParams['figure.figsize'] = 5, 8
gs = plt.GridSpec(1,1)
ax = plt.subplot(gs[0])
ax.hist(abs(np.exp(y)-1),bins = 20,normed=1,  cumulative = True, histtype = 'step', color = 'k',linewidth = 2,label="All Dec.") # weights = ratio_err,
# ax.hist(abs(ratio_dec18), bins = 20,normed=1,cumulative = True, linestyle = 'dashed', histtype = 'step', color = 'k', label="Dec. > 18") #  weights = ratio_err_dec18, 
# ax.hist(abs(ratio_less_dec18), bins = 20,normed=1,  cumulative = True, linestyle = 'dotted', histtype = 'step', color = 'k', label="Dec. < 18") # weights = ratio_err_less_dec18,
ax.set_title(input_mosaic+' Freq = '+str(freq_obs))
ax.set_ylim(0., 1.)
ax.set_xlim(0, 1.)
ax.legend(loc='upper right', fontsize=10) # make a legend in the best location
ax.set_xlabel('Pred. flux density / Obs. flux density', fontsize = 15)
plt.savefig(input_mosaic+'_'+suffix+'_'+str(freq_obs)+'MHz_cdf.png')

# Saving zero fits for each freq 
freq_list = np.array(['072-080MHz','080-088MHz','088-095MHz','095-103MHz','103-111MHz','111-118MHz','118-126MHz','126-134MHz','139-147MHz','147-154MHz','154-162MHz','162-170MHz','170-177MHz','177-185MHz','185-193MHz','193-200MHz','200-208MHz','208-216MHz','216-223MHz','223-231MHz'])

freq_str = input_mosaic.split("_")[1]

zerofits=fitsfile.replace(".fits","")+'_'+suffix+'_zero.fits'

if not os.path.exists(zerofits):
    print 'Making '+zerofits
    zero_fits = np.zeros(len(freq_list))
    zero_fits_err = np.zeros(len(freq_list))
    freqs = np.array([76,84,92,99,107,115,123,130,143,150,158,166,174,181,189,197,204,212,219,227])
else:
    print 'Reading in '+zerofits
    hdulist = fits.open(zerofits)
    tbdata = hdulist[1].data
    hdulist.close()
    zero_fits = np.array(tbdata['Zero_fit'])
    zero_fits_err = np.array(tbdata['Zero_fit_err'])

print 'Saving zero fits of this frequency to '+zerofits

freq_ind = np.where(freq_str == freq_list)


zero_fits[freq_ind] = poptzero[0]
zero_fits_err[freq_ind] = np.sqrt(pcovzero[0])

if options.printaverage:
    print zero_fits[freq_ind]

print 'End '+input_mosaic+': '+str(datetime.datetime.now())

col1 = fits.Column(name='Frequency', format = 'E', array = freqs)
col2 = fits.Column(name='Zero_fit', format = 'E', array = zero_fits)
col3 = fits.Column(name='Zero_fit_err', format = 'E', array = zero_fits_err)
cols = fits.ColDefs([col1,col2,col3])

tbhdu = fits.new_table(cols)    
tbhdu.writeto(zerofits, clobber = True) 

# plt.figure()
# plt.hist2d(dec,ratio,bins=25)
# plt.ylabel('Ratio')
# plt.xlabel('Dec')
# cb = plt.colorbar()
# cb.ax.set_ylabel('Number of sources')
# plt.show()

