#!/usr/bin/env python

# Correcting the declination dependent flux scale of the mosaics for GLEAM. 
# This code will calculate the ratio of flux density from SEDs of bright sources and the 
# measured flux density from Aegean. All sources have a VLSSr counterpart.
# It will then calculate the best fitting polynomial.
# Note that this should be run from directory structure that is above saving directories.
# J. R. Callingham 26/2/2015

import datetime
import numpy as np
import matplotlib as mpl 
mpl.use('Agg') # So does not use display
import matplotlib.pylab as plt
import scipy.optimize as opt
import scipy.stats as stats
from astropy.io import fits
from optparse import OptionParser
import os
import sys
import emcee
# import sedplots - ask Joe for a copy

print "#----------------------------------------------------------#"
print '''Fixing declination dependent flux scale in GLEAM mosaic. Ensure you have votables from Aegean. 
You need to already run the source finder Aegean on the mosiac and have *_comp.vot and *_isle.vot 
in your working directory. You get the *_isle.vot table from using the --island option in Aegean.
Also ensure that the file marco_all_VLSSsrcs.fits is in $MWA_CODE_BASE. You also need stilts and 
the python package emcee installed on your computer.'''

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('--mosaic',type="string", dest="mosaic",
                    help="The filename of the mosaic you want to read in.")
parser.add_option('--ratio_errors',action="store_true",dest="do_ratio_errors",default=True,
                    help="Calculate errors on model fits and ratio of it with image flux measurement (default = False)")
parser.add_option('--plot',action="store_true",dest="make_plots",default=False,
                    help="Make fit plots? (default = False)")
parser.add_option('--zenith',action="store_true",dest="zenith",default=False,
                    help="Calculate correction for the special case of zenith.")
(options, args) = parser.parse_args()

input_mosaic = options.mosaic

def redchisq(ydata,ymod,sd,deg):
    chisq=np.sum(((ydata-ymod)/sd)**2)
    nu=ydata.size-1-deg
    return [chisq, chisq/nu]#, chisq/nu


header = fits.getheader(input_mosaic+'.fits')
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

# Checking if file with ratios already exists. If they do, skip to straight fitting. 

if not os.path.exists(input_mosaic+'_fluxdentable_decut.fits'):

    print "#----------------------------------------------------------#"
    print 'Crossmatching mosaic with literature using stilts.'

    os.system('stilts tmatch2 in1='+input_mosaic+'_comp.vot in2='+input_mosaic+'_isle.vot join=1and2 find=best matcher=exact values1="island" values2="island" out='+input_mosaic+'_tot.vot')
    #os.system('stilts tskymatch2 in1=$MWA_CODE_BASE/marco_all_VLSSsrcs.fits in2='+input_mosaic+'_tot.vot out=marco_all_VLSSsrcs+'+input_mosaic+'.fits ra1=RAJ2000 dec1=DEJ2000 ra2=ra_1 dec2=dec_1 error=40')
    os.system('stilts tmatch2 matcher=skyellipse in1=$MWA_CODE_BASE/marco_all_VLSSsrcs.fits in2='+input_mosaic+'_tot.vot out=marco_all_VLSSsrcs+'+input_mosaic+'.fits values1="RAJ2000 DEJ2000 MajAxis MinAxis PA" values2="ra_1 dec_1 a b pa_1" params=20')

    hdulist = fits.open('marco_all_VLSSsrcs+'+input_mosaic+'.fits')
    hdulist.verify('fix')
    tbdata = hdulist[1].data
    hdulist.close()

    week=input_mosaic.split("_")[1][0:8]
    if Dec_strip == -40. or Dec_strip == -55. or Dec_strip == -72. or ( week != "20131107" and week != "20131111" and week != "20131125" and week != "20130822" ):
        print "Will automatically use corrections from another mosaic."
        sys.exit(0)

    print "#----------------------------------------------------------#"
    print 'Analysing '+input_mosaic

    VLSSr_Name = np.array(tbdata['ID_vlss'])
    RA = np.array(tbdata['RAJ2000_vlss']) #VLSSr positions
    Dec = np.array(tbdata['DEJ2000_vlss'])
    RA_NVSS = np.array(tbdata['RAJ2000'])
    RA_NVSS = np.where(np.isnan(RA_NVSS), 0, RA_NVSS)
    Dec_NVSS = np.array(tbdata['DEJ2000'])
    Dec_NVSS = np.where(np.isnan(Dec_NVSS), 0, Dec_NVSS)
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
    S_325 = np.array(tbdata['S_wsrt'])
    S_325 = np.where(np.isnan(S_325), 0, S_325)
    S_325_err = (0.06**2 + (4./S_325)**2)**0.5 # from eqn 9 Rengelink et al. (1997)
    S_196 = np.array(tbdata['peak_flux_1']) # MWA from aegean
    S_196_err = np.array(tbdata['err_peak_flux'])
    S_196_int = np.array(tbdata['int_flux_1'])
    S_196_int_err = np.array(tbdata['err_int_flux_1'])
    S_196_isle_int = np.array(tbdata['int_flux_2'])
    eta = np.array(tbdata['eta'])
    flags_1 = np.array(tbdata['flags_1'])
    semi_major  = np.array(tbdata['a'])
    semi_minor  = np.array(tbdata['b'])
    err_a = np.array(tbdata['err_a'])
    components = np.array(tbdata['components'])
    rms = np.array(tbdata['local_rms_1'])
    S_196_isle_int = S_196_isle_int / eta 
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

    freq = np.array([74., 80., 160., freq_obs, 325., 408., 843., 1400.])
    flux = np.vstack((S_74,S_80, S_160, S_196_int, S_325, S_408,S_843_north,S_1400))
    flux_err = np.vstack((S_74_err,S_80_err, S_160_err, S_196_int_err,S_325_err,
        S_408_err,S_843_north_err,S_1400_err))

    print "#----------------------------------------------------------#"
    print 'Fitting powerlaw to flux points, excluding MWA points'

    p0pow = [7,-0.7]

    def powlaw(freq, a, alpha): # defining powlaw as S = a*nu^alpha.
        return a*(freq**alpha)
    do_errors = True
    srcsind=[]
    alpha, redchisq_val, MWAfreqfit_predicted, MWAfreqfit_predicted_err, ratio, ratio_err, hour_angle, hour_angle_sym, az, alt= [np.zeros(np.shape(flux[1])[0]) for dummy in range(10)]
    for i in range(np.shape(flux[1])[0]): # arange(6040,6100):#

        fluxposind = np.where(flux[:,i] > 0)
        fluxplot = flux[:,i][fluxposind]
        freqplot = freq[fluxposind]
        flux_errplot = flux_err[:,i][fluxposind]
        ind_nomwa = np.where((freq != freq_obs) & (flux[:,i] > 0) & (freq != 80.) & (freq != 160.)& (freq != 325.)) # Fitting to only non zero and non_MWA points and non-texas or 
        fluxfit = flux[:,i][ind_nomwa]
        freqfit = freq[ind_nomwa]
        flux_errfit = flux_err[:,i][ind_nomwa]
        
        if len(fluxfit) >= 3 or (Dec[i] > 18. and isolated_flag[i] == True):
            
            try:
                poptpowlaw, pcovpowlaw = opt.curve_fit(powlaw, freqfit, fluxfit, p0 = p0pow, sigma = flux_errfit, maxfev = 10000)            
            except ValueError: # If curve fit can not find a good fit, skip the source.
                print 'Skipping because can not find good fit.'
                continue

            redchisq_val[i] = redchisq(fluxfit,powlaw(freqfit,*poptpowlaw),flux_errfit,2)[0]
            # if redchisq_val[i] <= 2.5 and err_a[i] >=0 and flags_1[i] == 0 and S_196_isle_int[i]/S_196[i] < 1.4 and S_196_int[i]/S_196[i] < 1.5 and poptpowlaw[1] > 0.1 and S_196[i] > 500.: #and S_196_int[i]/S_196[i] > 1. and S_196_int[i]/S_196[i] < 1.5 # Only want to find point sources that are well fitted by a powerlaw and have three or more points (excluding MWA points).
            # if redchisq_val[i] <= 2.5 and err_a[i] >=0 and flags_1[i] == 0 and components[i] == 1 and semi_major[i]/(2*semi_minor[i]) <= 1 and poptpowlaw[1] > 0.1 and S_196[i] > 5.:
            if redchisq_val[i] <= 2.5 and err_a[i] >=0 and flags_1[i] == 0 and components[i] == 1 and abs(poptpowlaw[1]) > 0.1 and 8*rms[i]/S_196_int[i] <= 1. and S_74[i] > 2.0:    #semi_major[i]/(2*semi_minor[i]) <= 1

                print VLSSr_Name[i]+' meets the criteria.'

                MWAfreqfit_predicted[i] = powlaw(freq_obs,*poptpowlaw)
                ratio[i] = MWAfreqfit_predicted[i] / S_196_int[i]
                alpha[i] = poptpowlaw[1]

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
                    j=0
                    for S_norm, specind in samples[np.random.randint(len(samples), size=100)]:
                        flux_store[j] = powlaw(freq_obs, S_norm,specind)
                        lower_flux_powlaw, upper_flux_powlaw = np.percentile(flux_store[:],[16,84], axis = 0)
                        j = j+1    
                    srcsind.append(i)

                    MWAfreqfit_predicted_err[i] = upper_flux_powlaw - lower_flux_powlaw
                    ratio_err[i] = ratio[i]*np.sqrt((S_196_int_err[i] / S_196_int[i])**2 + (MWAfreqfit_predicted_err[i] / MWAfreqfit_predicted[i])**2)
                    alpha[i] = specind
                    
                    # sedplots.sed(powlaw,poptpowlaw,freqplot,fluxplot,flux_errplot, freq_labels = True, savefig = False, title = VLSSr_Name[i]+r' $\alpha$ = '+str(round(alpha[i],3))+r' $ \chi_{\rm{red}}$  = '+str(round(redchisq_val[i])))#+' ObsID = '+str(aegeanfiles[j]))
                    # if not os.path.exists(os.getcwd()+'/figures/'):
                    #     os.makedirs(os.getcwd()+'/figures/')
                    # #     print 'Creating directory ', os.getcwd()+'/'+directory+'/figures/'+VLSSr_Name[i]+' and saving figures in png format with title names.'
                    # plt.savefig(os.getcwd()+'/figures/'+VLSSr_Name[i]+'.png')
                else:
                    srcsind.append(i)


        else:
            print 'Less than three flux values. Skipping...'

    # Saving file of sources into .fits

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
    col38 = fits.Column(name='S_325', format = 'E', array = S_325[srcsind])
    col39 = fits.Column(name='S_325_err', format = 'E', array = S_325_err[srcsind])
    col7 = fits.Column(name='S_408', format = 'E', array = S_408[srcsind])
    col8 = fits.Column(name='S_408_err', format = 'E', array = S_408_err[srcsind])
    col9 = fits.Column(name='S_843_north', format = 'E', array = S_843_north[srcsind])
    col10 = fits.Column(name='S_843_north_err', format = 'E', array = S_843_north_err[srcsind])
    col11 = fits.Column(name='S_1400_NVSS', format = 'E', array = S_1400[srcsind])
    col12 = fits.Column(name='S_1400_NVSS_err', format = 'E', array = S_1400_err[srcsind])
    col13 = fits.Column(name='RA', format = 'E', array = RA[srcsind]) # VLSSR
    col14 = fits.Column(name='Dec', format = 'E', array = Dec[srcsind]) # VLSSR
    col19 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_aegean_peak', format = 'E', array = S_196[srcsind])
    col20 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_err_aegean_peak', format = 'E', array = S_196_err[srcsind])
    col21 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_integrated_err_aegean', format = 'E', array = S_196_int_err[srcsind])
    col23 = fits.Column(name='RA_NVSS', format = 'E', array = RA_NVSS[srcsind])
    col24 = fits.Column(name='Dec_NVSS', format = 'E', array = Dec_NVSS[srcsind])
    col27 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_ISLE_integrated', format = 'E', array = S_196_isle_int[srcsind])
    col28 = fits.Column(name='redchisq', format = 'E', array = redchisq_val[srcsind])
    col29 = fits.Column(name='alpha', format = 'E', array = alpha[srcsind])
    col42 = fits.Column(name='rms', format = 'E', array = rms[srcsind])

    cols = fits.ColDefs([col1, col13, col14, col2, col43,
        col3, col4, col44, col19, col20, col21, col27, col5, col6, col30, col31,col32, col33,
        col38, col39, col7, col8, col9, col10, 
        col11, col12, col23, col24, col28, col29, col42])
    tbhdu = fits.new_table(cols)  
    print "#----------------------------------------------------------#"
    print 'Saving to a fits file.'  
    tbhdu.writeto(input_mosaic+'_fluxdentable.fits', clobber = True) 
    print 'Wrote to '+input_mosaic+'_fluxdentable.fits'
    print 'Note that you should eyeball dec V ratio to make sure sensible result.'

    # Making dec cut for sources with high SNR properties. Reading in empirical limts.

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
    Dec_cut = np.where((Dec[srcsind] > Dec_lim1) & (Dec[srcsind] < Dec_lim2) & (((RA[srcsind] > RA_lim1) & (RA[srcsind] < RA_lim2)) | ((RA[srcsind] > RA_lim3) & (RA[srcsind] < RA_lim4))))

    # Dec_cut = np.where((Dec[srcsind] > -26.7) & (Dec[srcsind] < -15))

    col1 = fits.Column(name='VLSSr Name', format = '22A', array = VLSSr_Name[srcsind][Dec_cut])
    col2 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_model', format = 'E', array = MWAfreqfit_predicted[srcsind][Dec_cut])
    col43 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_model_err', format = 'E', array = MWAfreqfit_predicted_err[srcsind][Dec_cut])
    col3 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_integrated_aegean', format = 'E', array = S_196_int[srcsind][Dec_cut])
    col4 = fits.Column(name='ratio', format = 'E', array = ratio[srcsind][Dec_cut])
    col44 = fits.Column(name='ratio_err', format = 'E', array = ratio_err[srcsind][Dec_cut])
    col5 = fits.Column(name='S_74', format = 'E', array = S_74[srcsind][Dec_cut])
    col6 = fits.Column(name='S_74_err', format = 'E', array = S_74_err[srcsind][Dec_cut])
    col30 = fits.Column(name='S_80', format = 'E', array = S_80[srcsind][Dec_cut])
    col31 = fits.Column(name='S_80_err', format = 'E', array = S_80_err[srcsind][Dec_cut])
    col32 = fits.Column(name='S_160', format = 'E', array = S_160[srcsind][Dec_cut])
    col33 = fits.Column(name='S_160_err', format = 'E', array = S_160_err[srcsind][Dec_cut])
    col38 = fits.Column(name='S_325', format = 'E', array = S_325[srcsind][Dec_cut])
    col39 = fits.Column(name='S_325_err', format = 'E', array = S_325_err[srcsind][Dec_cut])
    col7 = fits.Column(name='S_408', format = 'E', array = S_408[srcsind][Dec_cut])
    col8 = fits.Column(name='S_408_err', format = 'E', array = S_408_err[srcsind][Dec_cut])
    col9 = fits.Column(name='S_843_north', format = 'E', array = S_843_north[srcsind][Dec_cut])
    col10 = fits.Column(name='S_843_north_err', format = 'E', array = S_843_north_err[srcsind][Dec_cut])
    col11 = fits.Column(name='S_1400_NVSS', format = 'E', array = S_1400[srcsind][Dec_cut])
    col12 = fits.Column(name='S_1400_NVSS_err', format = 'E', array = S_1400_err[srcsind][Dec_cut])
    col13 = fits.Column(name='RA', format = 'E', array = RA[srcsind][Dec_cut]) # VLSSR
    col14 = fits.Column(name='Dec', format = 'E', array = Dec[srcsind][Dec_cut]) # VLSSR
    col19 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_aegean_peak', format = 'E', array = S_196[srcsind][Dec_cut])
    col20 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_err_aegean_peak', format = 'E', array = S_196_err[srcsind][Dec_cut])
    col21 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_integrated_err_aegean', format = 'E', array = S_196_int_err[srcsind][Dec_cut])
    col23 = fits.Column(name='RA_NVSS', format = 'E', array = RA_NVSS[srcsind][Dec_cut])
    col24 = fits.Column(name='Dec_NVSS', format = 'E', array = Dec_NVSS[srcsind][Dec_cut])
    col27 = fits.Column(name='S_'+str(int(round(freq_obs)))+'_ISLE_integrated', format = 'E', array = S_196_isle_int[srcsind][Dec_cut])
    col28 = fits.Column(name='redchisq', format = 'E', array = redchisq_val[srcsind][Dec_cut])
    col29 = fits.Column(name='alpha', format = 'E', array = alpha[srcsind][Dec_cut])
    col42 = fits.Column(name='rms', format = 'E', array = rms[srcsind][Dec_cut])

    cols = fits.ColDefs([col1, col13, col14, col2, col43,
        col3, col4, col44, col19, col20, col21, col27, col5, col6, col30, col31,col32, col33,
        col38, col39, col7, col8, col9, col10, 
        col11, col12, col23, col24, col28, col29, col42])#, col22])

    tbhdu = fits.new_table(cols)    
    tbhdu.writeto(input_mosaic+'_fluxdentable_decut.fits', clobber = True) 
    print 'Wrote to '+input_mosaic+'_fluxdentable_decut.fits'

print 'Working out best fit polynomial.'

hdulist = fits.open(input_mosaic+'_fluxdentable_decut.fits')
tbdata = hdulist[1].data
hdulist.close()
dec = np.array(tbdata['Dec'])
# Modified to use integrated flux densities
ratio = np.array(tbdata['S_'+str(int(round(freq_obs)))+'_model']/tbdata['S_'+str(int(round(freq_obs)))+'_integrated_aegean'])
ratio_err = np.array(tbdata['ratio_err'])

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

redchisq_decfits = np.zeros(6)
a_fit, b_fit, c_fit, d_fit, e_fit = [np.zeros(6) for i in range(5)] 

p_guess_zero = [ 1.5]
poptzero, pcovzero = opt.curve_fit(zero_curvefit, dec, ratio, p0 = p_guess_zero, sigma = ratio_err, maxfev = 10000)
redchisq_decfits[0] = redchisq(ratio,zero_curvefit(dec,*poptzero),ratio_err,2)[0]
a_fit[0] = poptzero[0]

p_guess_lin = [ 1.5,  -7e-02]
poptlin, pcovlin = opt.curve_fit(lin_curvefit, dec, ratio, p0 = p_guess_lin, sigma = ratio_err, maxfev = 10000)
redchisq_decfits[1] = redchisq(ratio,lin_curvefit(dec,*poptlin),ratio_err,2)[0]
a_fit[1], b_fit[1] = poptlin[0], poptlin[1]

p_guess_quad = [ 1.5,  -7e-02,  -2e-03]
poptquad, pcovquad = opt.curve_fit(quad_curvefit, dec, ratio, p0 = p_guess_quad, sigma = ratio_err, maxfev = 10000)
redchisq_decfits[2] = redchisq(ratio,quad_curvefit(dec,*poptquad),ratio_err,2)[0]
a_fit[2], b_fit[2], c_fit[2] = poptquad[0], poptquad[1], poptquad[2]

print input_mosaic+' quad_fit = '+str(poptquad) 

p_guess_cubic = [ 1.5,  -7e-04,  -2e-03, -5.e-05]
poptcubic, pcovcubic = opt.curve_fit(cubic_curvefit, dec, ratio, p0 = p_guess_cubic, sigma = ratio_err, maxfev = 10000)
redchisq_decfits[4] = redchisq(ratio,cubic_curvefit(dec,*poptcubic),ratio_err,2)[0]
a_fit[4], b_fit[4], c_fit[4], d_fit[4] = poptcubic[0], poptcubic[1], poptcubic[2], poptcubic[3]

print input_mosaic+' cubic_fit = '+str(poptcubic)

p_guess_quart = [1.5, 1e-02, 3e-03, 1e-04, 5e-06]
poptquart, pcovquart = opt.curve_fit(quart_curvefit, dec, ratio, p0 = p_guess_quart, sigma = ratio_err, maxfev = 10000)
redchisq_decfits[5] = redchisq(ratio,quart_curvefit(dec,*poptquart),ratio_err,2)[0]
a_fit[5], b_fit[5], c_fit[5], d_fit[5], e_fit[5] = poptquart[0], poptquart[1], poptquart[2], poptquart[3], poptquart[4]

print input_mosaic+' quart_fit = '+str(poptquart)

# Log fits

# log_ratio = np.log(ratio)
# log_ratio_err = ratio_err / ratio

# p_guess_quad = [ 1.5,  -7e-02,  -2e-03]
# log_poptquad, log_pcovquad = opt.curve_fit(quad_curvefit, dec, log_ratio, p0 = p_guess_quad, sigma = log_ratio_err, maxfev = 10000)

# p_guess_cubic = [ 1.5,  -7e-04,  -2e-03, -5.e-05]
# log_poptcubic, log_pcovcubic = opt.curve_fit(cubic_curvefit, dec, log_ratio, p0 = p_guess_cubic, sigma = log_ratio_err, maxfev = 10000)

w = 1. / ratio_err
SNR = np.log10(w)

if options.make_plots:

    # Reading in dec limits for plotting again in case the file does exist
    header = fits.getheader(input_mosaic+'.fits')
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

    cutdir=os.environ['MWA_CODE_BASE']

    centre_dec, freq_band, RA_lim1, RA_lim2, Dec_lim1, Dec_lim2 = np.loadtxt(cutdir+'/ra_dec_limits_polyderivation.dat',skiprows=2,unpack=True) 
    dec_freq_comb = [centre_dec, freq_band]
    cut_ind = np.where((centre_dec == Dec_strip) & (freq_band == subband))
    RA_lim1 = RA_lim1[cut_ind]
    RA_lim2 = RA_lim2[cut_ind]
    Dec_lim1 = Dec_lim1[cut_ind]
    Dec_lim2 = Dec_lim2[cut_ind]

    if options.zenith:

        p_guess_quad_zenith = [ 1.5, -1]
        poptquad_zenith, pcovquad_zenith = opt.curve_fit(quad_curvefit_zenith, dec, ratio, p0 = p_guess_quad_zenith, sigma = ratio_err, maxfev = 10000)
        redchisq_decfits[3] = redchisq(ratio,quad_curvefit_zenith(dec,*poptquad_zenith),ratio_err,2)[0]
        a_fit[3], c_fit[3] = poptquad_zenith[0], poptquad_zenith[1]

        plt.rcParams['figure.figsize'] = 20, 5 # Setting figure size. Have to close window for it to have effect.
        gs = plt.GridSpec(1,6)
        ax = plt.subplot(gs[0])
        ax1 = plt.subplot(gs[1])
        ax2 = plt.subplot(gs[2])
        ax3 = plt.subplot(gs[3])
        ax4 = plt.subplot(gs[4])
        ax5 = plt.subplot(gs[5])
        # ax.scatter(dec, ratio, marker='+',color = 'k',c=SNR, cmap=plt.cm.Greys)#, c=SNR, cmap=plt.cm.Greys)
        # ax1.scatter(dec, ratio, marker='+',color ='k',c=SNR, cmap=plt.cm.Greys)#, c=SNR, cmap=plt.cm.Greys)
        # ax2.scatter(dec, ratio, marker='+',color ='k',c=SNR, cmap=plt.cm.Greys)#, c=SNR, cmap=plt.cm.Greys)
        # ax3.scatter(dec, ratio, marker='+',color ='k',c=SNR, cmap=plt.cm.Greys)
        # ax4.scatter(dec, ratio, marker='+',color ='k',c=SNR, cmap=plt.cm.Greys)
        # ax5.scatter(dec, ratio, marker='+',color ='k',c=SNR, cmap=plt.cm.Greys)
        ax.scatter(dec, ratio, marker='o',color = 'k',c=SNR, cmap=plt.cm.Greys)#, c=SNR, cmap=plt.cm.Greys)
        ax1.scatter(dec, ratio, marker='o',color ='k',c=SNR, cmap=plt.cm.Greys)#, c=SNR, cmap=plt.cm.Greys)
        ax2.scatter(dec, ratio, marker='o',color ='k',c=SNR, cmap=plt.cm.Greys)#, c=SNR, cmap=plt.cm.Greys)
        ax3.scatter(dec, ratio, marker='o',color ='k',c=SNR, cmap=plt.cm.Greys)
        ax4.scatter(dec, ratio, marker='o',color ='k',c=SNR, cmap=plt.cm.Greys)
        ax5.scatter(dec, ratio, marker='o',color ='k',c=SNR, cmap=plt.cm.Greys)
        dec_long = np.arange(Dec_lim1,Dec_lim2,0.1)
        dec_long = np.array(dec_long)
        ax.plot(dec_long,np.ones(len(dec_long))*zero_curvefit(dec_long, *poptzero), 'saddlebrown', linewidth = 3, label="zeroth order fit")
        ax1.plot(dec_long,lin_curvefit(dec_long, *poptlin), 'darkblue', linewidth = 3, label="linear fit")
        ax2.plot(dec_long,quad_curvefit_zenith(dec_long, *poptquad_zenith), 'darkorange', linewidth = 3, label="Quadratic forced TP fit")
        ax3.plot(dec_long,quad_curvefit(dec_long, *poptquad), 'darkgreen', linewidth = 3, label="Quadratic fit")
        ax4.plot(dec_long,cubic_curvefit(dec_long, *poptcubic), 'darkred', linewidth = 3, label="Cubic fit")
        ax5.plot(dec_long,quart_curvefit(dec_long, *poptquart), 'darkmagenta', linewidth = 3, label="Quartic fit")
        ax.legend(loc='upper right', fontsize=10) # make a legend in the best location
        ax1.legend(loc='upper right', fontsize=10) # make a legend in the best location
        ax2.legend(loc='upper right', fontsize=10) # make a legend in the best location
        ax3.legend(loc='upper right', fontsize=10) # make a legend in the best location
        ax4.legend(loc='upper right', fontsize=10) # make a legend in the best location
        ax5.legend(loc='upper right', fontsize=10) # make a legend in the best location
        ax.tick_params(axis='y', labelsize=15)
        ax.tick_params(axis='x', labelsize=10)
        ax1.tick_params(axis='y', labelsize=15)
        ax1.tick_params(axis='x', labelsize=10)
        ax2.tick_params(axis='y', labelsize=15)
        ax2.tick_params(axis='x', labelsize=10)
        ax3.tick_params(axis='y', labelsize=15)
        ax3.tick_params(axis='x', labelsize=10)
        ax4.tick_params(axis='y', labelsize=15)
        ax4.tick_params(axis='x', labelsize=10)
        ax5.tick_params(axis='y', labelsize=15)
        ax5.tick_params(axis='x', labelsize=10)
        ax.set_xlabel('Dec. (degrees)', fontsize = 10)
        ax1.set_xlabel('Dec. (degrees)', fontsize = 10)
        ax2.set_xlabel('Dec. (degrees)', fontsize = 10)
        ax3.set_xlabel('Dec. (degrees)', fontsize = 10)
        ax4.set_xlabel('Dec. (degrees)', fontsize = 10)
        ax5.set_xlabel('Dec. (degrees)', fontsize = 10)
        ax.set_ylabel('Ratio', fontsize = 15)
        plt.savefig(input_mosaic+'_polyfits_int.png')

    else:

        plt.rcParams['figure.figsize'] = 20, 5 # Setting figure size. Have to close window for it to have effect.
        gs = plt.GridSpec(1,5)
        ax = plt.subplot(gs[0])
        ax1 = plt.subplot(gs[1])
        ax2 = plt.subplot(gs[2])
        ax3 = plt.subplot(gs[3])
        ax4 = plt.subplot(gs[4])
        # ax.errorbar(dec, ratio, ratio_err, marker='.',linestyle='none', color = 'k',alpha=0.5)#, c=SNR, cmap=plt.cm.Greys)
        # ax1.errorbar(dec, ratio,ratio_err, marker='.',linestyle='none', color ='k',alpha=0.5)#, c=SNR, cmap=plt.cm.Greys)
        # ax2.errorbar(dec, ratio,ratio_err, marker='.',linestyle='none',color ='k',alpha=0.5)#, c=SNR, cmap=plt.cm.Greys)
        # ax3.errorbar(dec, ratio, ratio_err,marker='.',linestyle='none',color ='k',alpha=0.5)
        # ax4.errorbar(dec, ratio, ratio_err,marker='.',linestyle='none',color ='k',alpha=0.5)
        ax.scatter(dec, ratio, marker='o',color = 'k',c=SNR, cmap=plt.cm.Greys)#, c=SNR, cmap=plt.cm.Greys)
        ax1.scatter(dec, ratio, marker='o',color ='k',c=SNR, cmap=plt.cm.Greys)#, c=SNR, cmap=plt.cm.Greys)
        ax2.scatter(dec, ratio, marker='o',color ='k',c=SNR, cmap=plt.cm.Greys)#, c=SNR, cmap=plt.cm.Greys)
        ax3.scatter(dec, ratio, marker='o',color ='k',c=SNR, cmap=plt.cm.Greys)
        ax4.scatter(dec, ratio, marker='o',color ='k',c=SNR, cmap=plt.cm.Greys)
        dec_long = np.arange(Dec_lim1,Dec_lim2,0.1)
        dec_long = np.array(dec_long)
        if ratio.max() > 4.0:
            ax.set_ylim(ratio.min(),2.5)
            ax1.set_ylim(ratio.min(),2.5)
            ax2.set_ylim(ratio.min(),2.5)
            ax3.set_ylim(ratio.min(),2.5)
            ax4.set_ylim(ratio.min(),2.5)
        ax.plot(dec_long,np.ones(len(dec_long))*zero_curvefit(dec_long, *poptzero), 'saddlebrown', linewidth = 3, label="zeroth order fit")
        ax1.plot(dec_long,lin_curvefit(dec_long, *poptlin), 'darkblue', linewidth = 3, label="linear fit")
        ax2.plot(dec_long,quad_curvefit(dec_long, *poptquad), 'darkgreen', linewidth = 3, label="Quadratic fit")
        ax3.plot(dec_long,cubic_curvefit(dec_long, *poptcubic), 'darkred', linewidth = 3, label="Cubic fit")
        ax4.plot(dec_long,quart_curvefit(dec_long, *poptquart), 'darkmagenta', linewidth = 3, label="Quartic fit")
        # ax2.plot(dec_long,np.exp(quad_curvefit(dec_long, *log_poptquad)), 'darkgreen', linestyle = '--', linewidth = 3, label="Quadratic fit")
        # ax3.plot(dec_long,np.exp(cubic_curvefit(dec_long, *log_poptcubic)), 'darkred', linestyle = '--', linewidth = 3, label="Cubic fit")
        ax.legend(loc='upper right', fontsize=10) # make a legend in the best location
        ax1.legend(loc='upper right', fontsize=10) # make a legend in the best location
        ax2.legend(loc='upper right', fontsize=10) # make a legend in the best location
        ax3.legend(loc='upper right', fontsize=10) # make a legend in the best location
        ax4.legend(loc='upper right', fontsize=10) # make a legend in the best location
        ax.tick_params(axis='y', labelsize=15)
        ax.tick_params(axis='x', labelsize=10)
        ax1.tick_params(axis='y', labelsize=15)
        ax1.tick_params(axis='x', labelsize=10)
        ax2.tick_params(axis='y', labelsize=15)
        ax2.tick_params(axis='x', labelsize=10)
        ax3.tick_params(axis='y', labelsize=15)
        ax3.tick_params(axis='x', labelsize=10)
        ax4.tick_params(axis='y', labelsize=15)
        ax4.tick_params(axis='x', labelsize=10)
        ax.set_xlabel('Dec. (degrees)', fontsize = 10)
        ax1.set_xlabel('Dec. (degrees)', fontsize = 10)
        ax2.set_xlabel('Dec. (degrees)', fontsize = 10)
        ax3.set_xlabel('Dec. (degrees)', fontsize = 10)
        ax4.set_xlabel('Dec. (degrees)', fontsize = 10)
        ax.set_ylabel('Ratio', fontsize = 15)
        cb = plt.colorbar(ax3.scatter(dec, ratio, marker='o',color ='k',c=SNR, cmap=plt.cm.Greys))
        cb.set_label('1/log(ratio_err)',fontsize = 15)
        plt.savefig(input_mosaic+'_polyfits_int.png')

fit_name = ['zeroth','linear','quadratic','quadratic_zenith','cubic','quartic'] 

print "#----------------------------------------------------------#"
print 'Saving correction to '+input_mosaic+'_poly_coefficients.fits'

col1 = fits.Column(name='fit', format = '16A', array = fit_name)
col2 = fits.Column(name='a', format = 'E', array = a_fit)
col3 = fits.Column(name='b', format = 'E', array = b_fit)
col4 = fits.Column(name='c', format = 'E', array = c_fit)
col5 = fits.Column(name='d', format = 'E', array = d_fit)
col6 = fits.Column(name='e', format = 'E', array = e_fit)
col7 = fits.Column(name='red_chi_sq', format = 'E', array = redchisq_decfits)
cols = fits.ColDefs([col1, col2, col3, col4, col5,col6,col7])
tbhdu = fits.new_table(cols)    
tbhdu.writeto(input_mosaic+'_poly_coefficients.fits', clobber = True) 
