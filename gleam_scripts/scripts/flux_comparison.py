#!/usr/bin/env python

# Checking flux scale of calibrated large mosaics to make sure it is consistent with derivation.

import datetime
import os
import emcee
import matplotlib
matplotlib.use('Agg')
import numpy as np
import matplotlib.pylab as plt
import scipy.optimize as opt
import scipy.stats as stats
from astropy.io import fits
from astropy.modeling import models, fitting
from optparse import OptionParser

# Setting font. If this breaks on the supercomputer, just uncomment these two lines.
# from matplotlib import rc
# rc('text', usetex=True)
# rc('font',**{'family':'serif','serif':['serif']})

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('--mosaic',type="string", dest="mosaic",
                    help="The filename of the mosaic you want to read in. Exclude file extension.")
parser.add_option('--ratio_errors',action="store_true",dest="do_ratio_errors",default=True,
                    help="Calculate errors on model fits and ratio of it with image flux measurement (default = True). Keep true if already have *fluxdentable in directory.")
parser.add_option('--int',action="store_true",dest="int",default=False,
                    help="Use integrated flux rather than peak flux (default = False)")
(options, args) = parser.parse_args()

input_mosaic = options.mosaic

print 'Before '+input_mosaic+': '+str(datetime.datetime.now())

# Checking if fluxdentable exists

if options.int:
    check_file = os.path.exists(input_mosaic+'_fluxdentable_int.fits')
else:
    check_file = os.path.exists(input_mosaic+'_fluxdentable_peak.fits')

if not check_file:

    # Getting freq.
    header = fits.getheader(input_mosaic+'.fits')
    try:
        freq_obs = header['CRVAL3']/1e6
    except:
        freq_obs = header['FREQ']/1e6

    os.system('stilts tmatch2 matcher=skyellipse in1=$MWA_CODE_BASE/marco_all_VLSSsrcs.fits in2='+input_mosaic+'.vot out=marco_all_VLSSsrcs+'+input_mosaic+'.fits values1="RAJ2000 DEJ2000 MajAxis MinAxis PA" values2="ra dec a b pa" params=20')

    hdulist = fits.open('marco_all_VLSSsrcs+'+input_mosaic+'.fits')
    hdulist.verify('fix')
    tbdata = hdulist[1].data
    hdulist.close()

    print "#----------------------------------------------------------#"
    print 'Analysing '+input_mosaic

    VLSSr_Name = np.array(tbdata['ID_vlss'])
    RA_VLSSr = np.array(tbdata['RAJ2000_vlss']) #VLSSr positions
    Dec_VLSSr = np.array(tbdata['DEJ2000_vlss'])
    RA = np.array(tbdata['RAJ2000'])
    RA = np.where(np.isnan(RA), 0, RA)
    Dec = np.array(tbdata['DEJ2000'])
    Dec = np.where(np.isnan(Dec), 0, Dec)
    S_74 = np.array(tbdata['S_vlss']) # Integrated flux of VLSSr.
    S_74_err = np.sqrt((np.array(tbdata['e_S_vlss'])**2 + (S_74*0.1)**2))
    S_1400 = np.array(tbdata['S'])
    S_1400 = np.where(np.isnan(S_1400), 0, S_1400)
    S_1400_err = np.array(tbdata['e_S'])
    S_1400_err = np.where(np.isnan(S_1400_err), 0, S_1400_err)
    S_843_north = np.array(tbdata['S_sumss_north'])
    S_843_north = np.where(np.isnan(S_843_north), 0, S_843_north)
    S_843_north_err = np.array(tbdata['e_S_sumss_north'])
    S_843_north_err = np.where(np.isnan(S_843_north_err), 0, S_843_north_err)
    S_408 = np.array(tbdata['S_mrc'])
    S_408 = np.where(np.isnan(S_408), 0, S_408)
    S_408_err = np.array(tbdata['e_S_mrc'])
    S_408_err = np.where(np.isnan(S_408_err), 0, S_408_err)
    S_160 = np.array(tbdata['S_culgoora160'])
    S_160 = np.where(np.isnan(S_160), 0, S_160)
    S_80 = np.array(tbdata['S_culgoora80'])
    S_80 = np.where(np.isnan(S_80), 0, S_80)
    # S_325 = np.array(tbdata['S_wsrt'])
    # S_325 = np.where(np.isnan(S_325), 0, S_325)
    # S_325_err = (0.06**2 + (4./S_325)**2)**0.5 # from eqn 9 Rengelink et al. (1997)
    S_196 = np.array(tbdata['peak_flux']) # MWA from aegean
    S_196_err = np.array(tbdata['err_peak_flux'])
    S_196_int = np.array(tbdata['int_flux'])
    S_196_int_err = np.array(tbdata['err_int_flux'])
    err_a = np.array(tbdata['err_a'])
    rms = np.array(tbdata['local_rms'])
    flags_1 = np.array(tbdata['flags'])
    isolated_flag = np.array(tbdata['isolated'])

    # Working out the uncertainties on CCA values
    S_160_err = np.zeros(len(S_160))
    S_80_err = np.zeros(len(S_80))
    for i in range(len(S_160)):
        if S_160[i] > 0:
            #fixing up errors as per Table 3 in Slee 1977. Assuming average of two
            if S_160[i] <= 3:
                S_160_err[i] = 0.27*S_160[i]
            elif S_160[i] > 3 and S_160[i] <= 5:
                S_160_err[i] = 0.23*S_160[i]
            elif S_160[i] > 5 and S_160[i] <= 12:
                S_160_err[i] = 0.17*S_160[i]
            elif S_160[i] > 12 and S_160[i] <= 20:
                S_160_err[i] = 0.10*S_160[i]
            elif S_160[i] > 20:
                S_160_err[i] = 0.9*S_160[i]

        if S_80[i] > 0:
            if S_80[i] <= 10:
                S_80_err[i] = 0.32*S_80[i]
            elif S_80[i] > 10 and S_80[i] <= 20:
                S_80_err[i] = 0.20*S_80[i]
            elif S_80[i] > 20:
                S_80_err[i] = 0.10*S_80[i]

    if options.int:
        flux_obs = S_196_int
        flux_obs_err = S_196_int_err
    else:
        flux_obs = S_196
        flux_obs_err = S_196_err

    freq = np.array([74., 80., 160., freq_obs, 408., 843., 1400.])
    flux = np.vstack((S_74,S_80, S_160, flux_obs, S_408,S_843_north,S_1400))
    flux_err = np.vstack((S_74_err,S_80_err, S_160_err, flux_obs_err,
        S_408_err,S_843_north_err,S_1400_err))

    print "#----------------------------------------------------------#"
    print 'Fitting powerlaw to flux points, excluding MWA points'

    p0pow = [7,-0.7]

    def redchisq(ydata,ymod,sd,deg):
        chisq=np.sum(((ydata-ymod)/sd)**2)
        nu=ydata.size-1-deg
        return [chisq, chisq/nu]#, chisq/nu

    def powlaw(freq, a, alpha): # defining powlaw as S = a*nu^alpha.
        return a*(freq**alpha)

    srcsind=[]
    alpha, redchisq_val, MWAfreqfit_predicted, MWAfreqfit_predicted_err, ratio, ratio_err, hour_angle, hour_angle_sym, az, alt= [np.zeros(np.shape(flux[1])[0]) for dummy in range(10)]

    for i in range(np.shape(flux[1])[0]):

        fluxposind = np.where(flux[:,i] > 0)
        fluxplot = flux[:,i][fluxposind]
        freqplot = freq[fluxposind]
        flux_errplot = flux_err[:,i][fluxposind]
        ind_nomwa = np.where((freq != freq_obs) & (flux[:,i] > 0) & (freq != 80.) & (freq != 160.)& (freq != 325.)) # Fitting to only non zero and non_MWA points and non-texas or 
        fluxfit = flux[:,i][ind_nomwa]
        freqfit = freq[ind_nomwa]
        flux_errfit = flux_err[:,i][ind_nomwa]

        if len(fluxfit) >= 3 or (Dec[i] > 18. and isolated_flag[i] == True and Dec[i] < 30.):
         
            try:
                poptpowlaw, pcovpowlaw = opt.curve_fit(powlaw, freqfit, fluxfit, p0 = p0pow, sigma = flux_errfit, maxfev = 10000)            
                redchisq_val[i] = redchisq(fluxfit,powlaw(freqfit,*poptpowlaw),flux_errfit,2)[0]
            except ValueError: # If curve fit can not find a good fit, skip the source.
                print 'Skipping because can not find good fit.'
                continue

            if redchisq_val[i] <= 2.5 and err_a[i] >=0 and flags_1[i] == 0 and abs(poptpowlaw[1]) > 0.1 and 8*rms[i]/flux_obs[i] <= 1. and S_74[i] > 2.0:

                print VLSSr_Name[i]+' meets the criteria.'

                MWAfreqfit_predicted[i] = powlaw(freq_obs,*poptpowlaw)
                ratio[i] = MWAfreqfit_predicted[i] / flux_obs[i]
                alpha[i] = poptpowlaw[1]
                srcsind.append(i)
                
                if options.do_ratio_errors:
                    
                    # Calculating uncertainties on fit and ratio

                    x = freqfit
                    y = fluxfit
                    yerr = flux_errfit

                    def lnlike(theta,x,y,yerr):
                        S_norm,specind= theta # Model parameters have to be included in lnlike. This implentation makes it veristile.
                        model = powlaw(x,S_norm,specind)
                        inv_sigma = 1.0/(yerr**2)
                        return -0.5*(np.sum((y-model)**2*inv_sigma - np.log(inv_sigma)))  

                    # Use the scipy.opt model to find the optimum of this likelihood function

                    nll = lambda *args: -lnlike(*args)
                    p0guess = list(poptpowlaw) # Guessing the parameters of the model. This can be educated guess (i.e from least-square fit)
                    result = opt.fmin(nll,p0guess, args=(x,y,yerr), full_output='true')
                    S_norm_ml, specind_ml = result[0]    

                    def lnprior(theta):
                        S_norm, specind = theta
                        if poptpowlaw[0]/100. < S_norm < poptpowlaw[0]*100. and abs(poptpowlaw[1]/100.) < abs(specind) < abs(poptpowlaw[1]*100.):
                            return 0.00    
                        return -np.inf

                    # Combining this prior with the definition of the likelihood function, the probablity fucntion is:

                    def lnprob(theta, x, y, yerr):
                        lp = lnprior(theta)
                        if not np.isfinite(lp):
                            return -np.inf
                        return lp + lnlike(theta, x, y, yerr)

                    # Now implement emcee

                    ndim, nwalkers, nsteps =  2, 100, 500

                    # Initialising the walkers in a Gaussian ball around maximum likelihood result
                    pos = [result[0]+ 1e-4*np.random.randn(ndim) for p in range(nwalkers)]

                    # Next two lines useful for debugging if emcee falls over
                    # print 'lnprior1', map(lambda p: lnprior(p), pos)
                    # print 'lnlike', map(lambda p: lnlike(p, x, y, yerr), pos)

                    # print "Before emcee: "+str(datetime.datetime.now())
                    sampler = emcee.EnsembleSampler(nwalkers, ndim, lnprob, args = (x,y,yerr))
                    sampler.run_mcmc(pos, nsteps) # This is the workhorse step.
                    # print "After emcee: "+str(datetime.datetime.now())

                    # Now plotting the walks of the walkers with each step, for each parameter. 
                    # If they have converged on a good value they should have clumped together.

                    # fig = plt.figure(2,figsize=(10, 10))
                    # fig.clf()
                    # for j in range(ndim):
                    #     ax = fig.add_subplot(ndim,1,j+1)
                    #     ax.plot(np.array([sampler.chain[:,i,j] for i in range(nsteps)]),"k", alpha = 0.3)
                    #     ax.set_ylabel((r'$S_{norm}$',r'$\alpha$')[j], fontsize = 15)
                            
                    # Usually burn in period is well and truly over by 300 steps. So I will exclude those.
                    samples = sampler.chain[:,200:,:].reshape((-1,ndim))

                    # Plotting the histograms of the fit.
                    # trifig = triangle.corner(samples, labels = [r'$S_{norm}$',r'$\alpha$'])

                    # Finally to get the final uncertainties you do
                    S_norm_powlaw_mcmc, specind_powlaw_mcmc = map(lambda v: (v[1], v[2]-v[1], v[1]-v[0]), zip(*np.percentile(samples,[16,50,84], axis = 0))) # Uncertainites based on the 16th, 50th and 84th percentile.
                        
                    # Finding upper (84th percentile) and lower (16th percentile) values for all frequencies
                    fit_powlaw = [S_norm_powlaw_mcmc[0], specind_powlaw_mcmc[0]]
                    
                    # Calculating uncertainity at 
                    flux_store = np.zeros((100,1))
                    lower_flux_powlaw, upper_flux_powlaw = np.zeros(1), np.zeros(1)
                    ii=0
                    for S_norm, specind in samples[np.random.randint(len(samples), size=100)]:
                        flux_store[ii] = powlaw(freq_obs, S_norm,specind)
                        lower_flux_powlaw, upper_flux_powlaw = np.percentile(flux_store[:],[16,84], axis = 0)
                        ii = ii+1    

                    MWAfreqfit_predicted_err[i] = upper_flux_powlaw - lower_flux_powlaw
                    ratio_err[i] = ratio[i]*np.sqrt((flux_obs_err[i] / flux_obs[i])**2 + (MWAfreqfit_predicted_err[i] / MWAfreqfit_predicted[i])**2)
                    alpha[i] = specind
                    
                    # sedplots.sed(powlaw,poptpowlaw,freqplot,fluxplot,flux_errplot, freq_labels = True, savefig = False, title = VLSSr_Name[i]+r' $\alpha$ = '+str(round(alpha[i],3))+r' $ \chi_{\rm{red}}$  = '+str(round(redchisq_val[i])))#+' ObsID = '+str(aegeanfiles[j]))
                    # if not os.path.exists(os.getcwd()+'/figures/'):
                    #     os.makedirs(os.getcwd()+'/figures/')
                    # #     print 'Creating directory ', os.getcwd()+'/'+directory+'/figures/'+VLSSr_Name[i]+' and saving figures in png format with title names.'
                    # plt.savefig(os.getcwd()+'/figures/'+VLSSr_Name[i]+'.png')
        else:
            print 'Less than three flux values. Skipping...'

                # sedplots.sed(powlaw,poptpowlaw,freqplot,fluxplot,flux_errplot, freq_labels = True, savefig = False, title = VLSSr_Name[i]+r' $\alpha$ = '+str(round(alpha[i],3))+r' $ \chi_{\rm{red}}$  = '+str(round(redchisq_val[i],2)))#+' ObsID = '+str(aegeanfiles[j]))
                # if not os.path.exists(os.getcwd()+'/sed_figures/'):
                #     os.makedirs(os.getcwd()+'/sed_figures/')
                #     print 'Creating directory ', os.getcwd()+'/sed_figures/'+VLSSr_Name[i]+' and saving figures in png format with title names.'
                # plt.savefig(os.getcwd()+'/sed_figures/'+VLSSr_Name[i]+'.png')

    col1 = fits.Column(name='VLSSr Name', format = '22A', array = VLSSr_Name[srcsind])
    col2 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_model', format = 'E', array = MWAfreqfit_predicted[srcsind])
    col43 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_model_err', format = 'E', array = MWAfreqfit_predicted_err[srcsind])
    col3 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_integrated_aegean', format = 'E', array = S_196_int[srcsind])
    col4 = fits.Column(name='ratio', format = 'E', array = ratio[srcsind])
    col44 = fits.Column(name='ratio_err', format = 'E', array = ratio_err[srcsind])
    col5 = fits.Column(name='S_74', format = 'E', array = S_74[srcsind])
    col6 = fits.Column(name='S_74_err', format = 'E', array = S_74_err[srcsind])
    col30 = fits.Column(name='S_80', format = 'E', array = S_80[srcsind])
    col31 = fits.Column(name='S_80_err', format = 'E', array = S_80_err[srcsind])
    col32 = fits.Column(name='S_160', format = 'E', array = S_160[srcsind])
    col33 = fits.Column(name='S_160_err', format = 'E', array = S_160_err[srcsind])
    col7 = fits.Column(name='S_408', format = 'E', array = S_408[srcsind])
    col8 = fits.Column(name='S_408_err', format = 'E', array = S_408_err[srcsind])
    col9 = fits.Column(name='S_843_north', format = 'E', array = S_843_north[srcsind])
    col10 = fits.Column(name='S_843_north_err', format = 'E', array = S_843_north_err[srcsind])
    col11 = fits.Column(name='S_1400_NVSS', format = 'E', array = S_1400[srcsind])
    col12 = fits.Column(name='S_1400_NVSS_err', format = 'E', array = S_1400_err[srcsind])
    col13 = fits.Column(name='RA', format = 'E', array = RA[srcsind])
    col14 = fits.Column(name='Dec', format = 'E', array = Dec[srcsind])
    col19 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_aegean_peak', format = 'E', array = S_196[srcsind])
    col20 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_err_aegean_peak', format = 'E', array = S_196_err[srcsind])
    col21 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_integrated_err_aegean', format = 'E', array = S_196_int_err[srcsind])
    col23 = fits.Column(name='RA_NVSS', format = 'E', array = RA[srcsind])
    col24 = fits.Column(name='Dec_NVSS', format = 'E', array = Dec[srcsind])
    col28 = fits.Column(name='redchisq', format = 'E', array = redchisq_val[srcsind])
    col29 = fits.Column(name='alpha', format = 'E', array = alpha[srcsind])
    col42 = fits.Column(name='rms', format = 'E', array = rms[srcsind])

    cols = fits.ColDefs([col1, col13, col14, col2, col43,
        col3, col4, col44, col19, col20, col21, col5, col6, col30, col31,col32, col33,
        col7, col8, col9, col10, col11, col12, col23, col24, col28, col29, col42])#, col22])
    
    tbhdu = fits.new_table(cols)
    if options.int:
        tbhdu.writeto(input_mosaic+'_fluxdentable_int.fits', clobber = True) 
        print 'Wrote to '+input_mosaic+'_fluxdentable_int.fits'
    else:
        tbhdu.writeto(input_mosaic+'_fluxdentable_peak.fits', clobber = True) 
        print 'Wrote to '+input_mosaic+'_fluxdentable_peak.fits'
else:
    print input_mosaic+'_fluxdentable* exists. Will not recalculate errors but read in existing table.'

hdulist = fits.open(input_mosaic+'_fluxdentable.fits')
tbdata = hdulist[1].data
hdulist.close()
dec = np.array(tbdata['Dec'])
ratio = np.array(tbdata['ratio'])
ratio_err = np.array(tbdata['ratio_err'])

# Applying Dec cuts if just looking at non-massive mosaic.
''' # 
freq_obs = freqs[freq_ind]

if 72. < freq_obs < 103.:
    freq_cut_ind = 1
elif 103.01 < freq_obs < 134.:
    freq_cut_ind = 2
elif 139. < freq_obs < 170.:
    freq_cut_ind = 3
elif 170.01 < freq_obs < 200.:
    freq_cut_ind = 4
elif 200.01 < freq_obs < 231.:
    freq_cut_ind = 5

cutdir=os.environ['MWA_CODE_BASE']

centre_dec, freq_band, RA_lim1, RA_lim2, Dec_lim1, Dec_lim2 = np.loadtxt(cutdir+'/ra_dec_limits_polyderivation.dat',skiprows=2,unpack=True) 

dec_freq_comb = [centre_dec, freq_band]
cut_ind = np.where((centre_dec == Dec_strip) & (freq_band == subband))
RA_lim1 = RA_lim1[cut_ind]
RA_lim2 = RA_lim2[cut_ind]
Dec_lim1 = Dec_lim1[cut_ind]
Dec_lim2 = Dec_lim2[cut_ind]

#  cuts -- pretty much universal since we'll never want to use the Galactic plane to do this
# Set to 22h - 04h
if RA_lim1 > RA_lim2:
# i.e. we're crossing RA 0
    RA_lim3 = 0
    RA_lim4 = RA_lim2
    RA_lim2 = 360
else:
    RA_lim3 = RA_lim1
    RA_lim4 = RA_lim2

cut_ind = np.where((Dec[srcsind] > Dec_lim1) & (Dec[srcsind] < Dec_lim2) & (((RA[srcsind] > RA_lim1) & (RA[srcsind] < RA_lim2)) | ((RA[srcsind] > RA_lim3) & (RA[srcsind] < RA_lim4))))

dec = dec[cut_ind]
ratio = ratio[cut_ind]
ratio_err = ratio_err[cut_ind]
'''
def zero_curvefit(dec,a):
    return a

def lin_curvefit(dec, a, b): # defining quadratic
    return b*dec + a

def quad_curvefit(dec, a, b, c): # defining quadratic
    return c*np.power(dec,2) + b*dec + a

def quad_curvefit_zenith(dec, a, c): # defining quadratic
    return c*(np.power(dec,2) + 53.4*dec) + a

def cubic_curvefit(dec, a, b, c, d): # defining cubic
    return d*np.power(dec,3) + c*np.power(dec,2) + b*dec + a

def quart_curvefit(dec, a, b, c, d, e): # defining quart
    return e*np.power(dec,4) + d*np.power(dec,3) + c*np.power(dec,2) + b*dec + a

# ratio_err = ratio_err / ratio
# ratio = np.log(ratio)

a_fit, b_fit, c_fit, d_fit, e_fit = [np.zeros(2) for t in range(5)] 

p_guess_zero = [ 1.5]
poptzero, pcovzero = opt.curve_fit(zero_curvefit, dec, np.log(ratio), p0 = p_guess_zero,  maxfev = 10000)
a_fit[0] = poptzero[0]

p_guess_lin = [ 1.0,  7e-02]
poptlin, pcovlin = opt.curve_fit(lin_curvefit, dec, np.log(ratio), p0 = p_guess_lin, maxfev = 10000)
a_fit[1], b_fit[1] = poptlin[0], poptlin[1]

# Fitting ratio properly
if options.do_ratio_errors:
    x = dec
    yerr = ratio_err / ratio
    y = np.log(ratio)

    def lnlike(theta,x,y,yerr):
        a = theta # Model parameters have to be included in lnlike. This implentation makes it veristile.
        model = zero_curvefit(x,a)
        inv_sigma = 1.0/(yerr**2)
        return -0.5*(np.sum((y-model)**2*inv_sigma - np.log(inv_sigma)))  

    # Use the scipy.opt model to find the optimum of this likelihood function

    nll = lambda *args: -lnlike(*args)
    p0guess = list(poptzero) # Guessing the parameters of the model. This can be educated guess (i.e from least-square fit)
    result = opt.fmin(nll,p0guess, args=(x,y,yerr), full_output='true')
    a_ml = result[0]    

    def lnprior(theta):
        a = theta
        if abs(poptzero[0]/100.) < abs(a) < abs(poptzero[0]*100.):
            return 0.00    
        return -np.inf

    # Combining this prior with the definition of the likelihood function, the probablity fucntion is:

    def lnprob(theta, x, y, yerr):
        lp = lnprior(theta)
        if not np.isfinite(lp):
            return -np.inf
        return lp + lnlike(theta, x, y, yerr)

    # Now implement emcee

    ndim, nwalkers, nsteps =  1, 200, 1000

    # Initialising the walkers in a Gaussian ball around maximum likelihood result
    pos = [result[0]+ 1e-4*np.random.randn(ndim) for p in range(nwalkers)]

    # Next two lines useful for debugging if emcee falls over
    # print 'lnprior1', map(lambda p: lnprior(p), pos)
    # print 'lnlike', map(lambda p: lnlike(p, x, y, yerr), pos)

    # print "Before emcee: "+str(datetime.datetime.now())
    sampler = emcee.EnsembleSampler(nwalkers, ndim, lnprob, args = (x,y,yerr))
    sampler.run_mcmc(pos, nsteps) # This is the workhorse step.
    # print "After emcee: "+str(datetime.datetime.now())

    # Now plotting the walks of the walkers with each step, for each parameter. 
    # If they have converged on a good value they should have clumped together.

    # fig = plt.figure(2,figsize=(10, 10))
    # fig.clf()
    # for j in range(ndim):
    #     ax = fig.add_subplot(ndim,1,j+1)
    #     ax.plot(np.array([sampler.chain[:,i,j] for i in range(nsteps)]),"k", alpha = 0.3)
    #     ax.set_ylabel((r'a')[j], fontsize = 15)
            
    # Usually burn in period is well and truly over by 300 steps. So I will exclude those.
    samples = sampler.chain[:,200:,:].reshape((-1,ndim))

    # Plotting the histograms of the fit.
    # trifig = triangle.corner(samples, labels = ['a'])

    # Finally to get the final uncertainties you do
    a_mcmc = map(lambda v: (v[1], v[2]-v[1], v[1]-v[0]), zip(*np.percentile(samples,[16,50,84], axis = 0))) # Uncertainites based on the 16th, 50th and 84th percentile.
    print 'a_mcmc = '+ str(a_mcmc)

def hist_norm_height(n,bins,const):
    ''' Function to normalise bin height by a constant. 
        Needs n and bins from np.histogram.'''

    n = np.repeat(n,2)
    n = np.float32(n) / const
    new_bins = [bins[0]]
    new_bins.extend(np.repeat(bins[1:],2))
    
    return n,new_bins[:-1]

# # Unlogging ratios after fits
# ratio = np.exp(ratio)
# ratio_err = ratio_err * ratio

if options.do_ratio_errors:
    a_mcmc_plot = np.exp(a_mcmc[0][0])
    a_mcmc_plot_err = a_mcmc[0][1] * a_mcmc_plot

# Identifying sources above and below dec. 18 deg. 

dec18_ind = np.where(dec >= 18.)
ratio_dec18 = ratio[dec18_ind]
ratio_err_dec18 = ratio_err[dec18_ind]
dec18_less_ind = np.where(dec < 18.)
ratio_less_dec18 = ratio[dec18_less_ind]
ratio_err_less_dec18 = ratio_err[dec18_less_ind]

SNR = ratio_err

# poptzero_ratio_dec18, pcovzero_ratio_dec18 = opt.curve_fit(zero_curvefit, dec[dec18_ind], ratio_dec18, p0 = p_guess_zero, sigma = ratio_err_dec18, maxfev = 10000)
# poptzero_ratio_less_dec18, pcovzero_ratio_less_dec18 = opt.curve_fit(zero_curvefit, dec[dec18_less_ind], ratio_less_dec18, p0 = p_guess_zero, sigma = ratio_err_less_dec18, maxfev = 10000)

plt.rcParams['figure.figsize'] = 12, 5 # Setting figure size. Have to close window for it to have effect.
gs = plt.GridSpec(1,2, wspace = 0, width_ratios = [3,1])
ax = plt.subplot(gs[0])
ax1 = plt.subplot(gs[1])
ax.scatter(dec, ratio, marker='o', c=SNR, cmap=plt.cm.Greys_r, norm=matplotlib.colors.LogNorm())#, c=SNR, cmap=plt.cm.Greys)
dec_long = np.arange(min(dec)+0.07*min(dec),max(dec)+0.10*max(dec),0.1)
dec_long = np.array(dec_long)
if options.do_ratio_errors:
    ax.plot(dec_long,np.ones(len(dec_long))*zero_curvefit(dec_long, a_mcmc_plot), 'saddlebrown', linewidth = 3)
else:
    ax.plot(dec_long,np.ones(len(dec_long))*zero_curvefit(dec_long, *poptzero), 'saddlebrown', linewidth = 3, label="All Dec.")
# ax.plot(dec_long,np.ones(len(dec_long))*zero_curvefit(dec_long, *poptzero_ratio_dec18), 'crimson', linewidth = 3, label="Dec. > 18")
# ax.plot(dec_long,np.ones(len(dec_long))*zero_curvefit(dec_long, *poptzero_ratio_less_dec18), 'navy', linewidth = 3, label="Dec. < 18")
ax.legend(loc='upper right', fontsize=10) # make a legend in the best location
ax.tick_params(axis='y', labelsize=15)
ax.tick_params(axis='x', labelsize=15)
ax.set_xlim(min(dec)+0.07*min(dec), max(dec)+0.10*max(dec))
y_lim_plot = [0.4,1.6]
ax.set_ylim(y_lim_plot)
ax.set_xlabel('Dec. (degrees)', fontsize = 15)
ax.set_ylabel('Pred. flux density / Obs. flux density', fontsize = 15)
n, bins = np.histogram(ratio, bins = 20,weights = ratio_err)
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
ax1.step(n, bins, color = 'k',linewidth = 2, label="All Dec.")
ax1.plot(g(np.linspace(y_lim_plot[0],y_lim_plot[1],100)),np.linspace(y_lim_plot[0],y_lim_plot[1],100), 'r-', lw=2, label='Gaussian')
ax1.step(n_dec18, bins_dec18, color = 'k', linestyle = 'dashed', label="Dec. > 18")
ax1.step(n_less_dec18, bins_less_dec18, color = 'k',linestyle = 'dotted', label="Dec. < 18")
ax1.legend(loc='upper right', fontsize=10) # make a legend in the best location
ax1.yaxis.set_ticklabels([])   # remove the major ticks
ax1.set_ylim(y_lim_plot)
start_x, end_x = ax1.get_xlim()
start_y, end_y = ax1.get_ylim()
ax1.xaxis.set_ticks([0.5, 1.0])
n_range = np.arange(start_x, end_x,0.01)
ax.set_title(input_mosaic)
ax1.set_title(r'$\mu$ = '+str(round(g.mean[0],4))+r' $\sigma$ = '+str(round(g.stddev[0],4)), fontsize = 10)
if options.do_ratio_errors:
    ax1.plot(n_range,np.ones(len(n_range))*zero_curvefit(n_range, a_mcmc_plot), 'saddlebrown', linewidth = 3)
else:
    ax1.plot(n_range,np.ones(len(n_range))*zero_curvefit(n_range, *poptzero), 'saddlebrown', linewidth = 3)
# ax1.xaxis.set_major_locator(MaxNLocator(prune='lower'))
cb = plt.colorbar(ax.scatter(dec, ratio, marker='o',color ='k',c=SNR, cmap=plt.cm.Greys_r, norm=matplotlib.colors.LogNorm()))
cb.set_label('error (Pred. flux density / Obs. flux density)',fontsize = 15)
plt.savefig(input_mosaic+'_fits.png')

# Plotting CDF

plt.rcParams['figure.figsize'] = 5, 8
gs = plt.GridSpec(1,1)
ax = plt.subplot(gs[0])
ax.hist(abs(ratio-1),bins = 20,normed=1,  cumulative = True, histtype = 'step', color = 'k',linewidth = 2,label="All Dec.") # weights = ratio_err,
# ax.hist(abs(ratio_dec18), bins = 20,normed=1,cumulative = True, linestyle = 'dashed', histtype = 'step', color = 'k', label="Dec. > 18") #  weights = ratio_err_dec18, 
# ax.hist(abs(ratio_less_dec18), bins = 20,normed=1,  cumulative = True, linestyle = 'dotted', histtype = 'step', color = 'k', label="Dec. < 18") # weights = ratio_err_less_dec18,
ax.set_title(input_mosaic)
ax.set_ylim(0., 1.)
ax.set_xlim(0, 1.)
ax.legend(loc='upper right', fontsize=10) # make a legend in the best location
ax.set_xlabel('Pred. flux density / Obs. flux density', fontsize = 15)
plt.savefig(input_mosaic+'_cdf.png')

# Saving zero fits for each freq 
week=input_mosaic.split("_")[0]
freq_list = np.array(['072-080MHz','080-088MHz','088-095MHz','095-103MHz','103-111MHz','111-118MHz','118-126MHz','126-134MHz','139-147MHz','147-154MHz','154-162MHz','162-170MHz','170-177MHz','177-185MHz','185-193MHz','193-200MHz','200-208MHz','208-216MHz','216-223MHz','223-231'])

if not os.path.exists(week+'_zero.fits'):
    print 'Making '+week+'_zero.fits'
    zero_fits = np.zeros(len(freq_list))
    zero_fits_err = np.zeros(len(freq_list))
    freqs = np.array([76,84,92,99,107,115,123,130,143,150,158,166,174,181,189,197,204,212,219,227])
else:
    print 'Reading in '+week+'_zero.fits'
    hdulist = fits.open(week+'_zero.fits')
    tbdata = hdulist[1].data
    hdulist.close()
    zero_fits = np.array(tbdata['Zero_fit'])
    zero_fits_err = np.array(tbdata['Zero_fit_err'])

print 'Saving zero fits of this frequency to '+week+'_zero.fits'

freq_str = input_mosaic.split("_")[1]

freq_ind = np.where(freq_str == freq_list)

if options.do_ratio_errors:
    zero_fits[freq_ind] = a_mcmc_plot
    zero_fits_err[freq_ind] = a_mcmc_plot_err
else:
    zero_fits[freq_ind] = poptzero[0]
    zero_fits_err[freq_ind] = np.sqrt(pcovzero[0])

print 'End '+input_mosaic+': '+str(datetime.datetime.now())

col1 = fits.Column(name='Frequency', format = 'E', array = freqs)
col2 = fits.Column(name='Zero_fit', format = 'E', array = zero_fits)
col3 = fits.Column(name='Zero_fit_err', format = 'E', array = zero_fits_err)
cols = fits.ColDefs([col1,col2,col3])

tbhdu = fits.new_table(cols)    
tbhdu.writeto('zerofits.fits', clobber = True) 

# plt.figure()
# plt.hist2d(dec,ratio,bins=25)
# plt.ylabel('Ratio')
# plt.xlabel('Dec')
# cb = plt.colorbar()
# cb.ax.set_ylabel('Number of sources')
# plt.show()

