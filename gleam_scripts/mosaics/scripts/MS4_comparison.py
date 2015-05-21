# !/bin/python
# Program for fitting and plotting SEDs for MS4 sources.

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import ticker
import scipy.optimize as opt
import scipy.stats as stats
from astropy.io import fits
import scipy.special as special # For access to the incomplete gamma function.
from collections import OrderedDict
from optparse import OptionParser
# import re

# To plot labels in serif rather than default.
# from matplotlib import rc
# rc('text', usetex=True)
# rc('font',**{'family':'serif','serif':['serif']})

usage="Usage: %prog [options] <file>\n"
parser = OptionParser(usage=usage)
parser.add_option('--int',action="store_true",dest="int",default=False,
                    help="Use integrated flux rather than peak flux (default = False)")
(options, args) = parser.parse_args()

print "#----------------------------------------------------------#"
print 'Reading in the observations'

hdulist = fits.open('crossmatching/ms4/tot_mwa_154-162MHzbase+MS4.fits')
tbdata = hdulist[1].data
hdulist.close()
freqs = np.array([76,84,92,99,107,115,123,130,143,150,158,166,174,181,189,197,204,212,219,227])

if options.int:
    type_flux = 'int'
else:
    type_flux = 'peak'

S_158 = np.array(tbdata[type_flux+'_flux_1'])
S_158_err = np.array(tbdata['err_'+type_flux+'_flux_1']) + S_158*0.025
S_076 = np.array(tbdata[type_flux+'_flux_2'])
S_076_err = np.array(tbdata['err_'+type_flux+'_flux_2']) + S_076*0.025
S_084 = np.array(tbdata[type_flux+'_flux_3'])
S_084_err = np.array(tbdata['err_'+type_flux+'_flux_3']) + S_084*0.025
S_092 = np.array(tbdata[type_flux+'_flux_4'])
S_092_err = np.array(tbdata['err_'+type_flux+'_flux_4']) + S_092*0.025
S_099 = np.array(tbdata[type_flux+'_flux_5'])
S_099_err = np.array(tbdata['err_'+type_flux+'_flux_5']) + S_099*0.025
S_107 = np.array(tbdata[type_flux+'_flux_6'])
S_107_err = np.array(tbdata['err_'+type_flux+'_flux_6']) + S_107*0.025
S_115 = np.array(tbdata[type_flux+'_flux_7'])
S_115_err = np.array(tbdata['err_'+type_flux+'_flux_7']) + S_115*0.025
S_123 = np.array(tbdata[type_flux+'_flux_8'])
S_123_err = np.array(tbdata['err_'+type_flux+'_flux_8']) + S_123*0.025
S_130 = np.array(tbdata[type_flux+'_flux_9'])
S_130_err = np.array(tbdata['err_'+type_flux+'_flux_9']) + S_130*0.025
S_143 = np.array(tbdata[type_flux+'_flux_10'])
S_143_err = np.array(tbdata['err_'+type_flux+'_flux_10']) + S_143*0.025
S_150 = np.array(tbdata[type_flux+'_flux_11'])
S_150_err = np.array(tbdata['err_'+type_flux+'_flux_11']) + S_150*0.025
S_166 = np.array(tbdata[type_flux+'_flux_12'])
S_166_err = np.array(tbdata['err_'+type_flux+'_flux_12']) + S_166*0.025
S_174 = np.array(tbdata[type_flux+'_flux_13'])
S_174_err = np.array(tbdata['err_'+type_flux+'_flux_13']) + S_174*0.025
S_181 = np.array(tbdata[type_flux+'_flux_14'])
S_181_err = np.array(tbdata['err_'+type_flux+'_flux_14']) + S_181*0.025
S_189 = np.array(tbdata[type_flux+'_flux_15'])
S_189_err = np.array(tbdata['err_'+type_flux+'_flux_15']) + S_189*0.025
S_197 = np.array(tbdata[type_flux+'_flux_16'])
S_197_err = np.array(tbdata['err_'+type_flux+'_flux_16']) + S_197*0.025
S_204 = np.array(tbdata[type_flux+'_flux_17'])
S_204_err = np.array(tbdata['err_'+type_flux+'_flux_17']) + S_204*0.025
S_212 = np.array(tbdata[type_flux+'_flux_18'])
S_212_err = np.array(tbdata['err_'+type_flux+'_flux_18']) + S_212*0.025
S_219 = np.array(tbdata[type_flux+'_flux_19'])
S_219_err = np.array(tbdata['err_'+type_flux+'_flux_19']) + S_219*0.025
S_227 = np.array(tbdata[type_flux+'_flux_20'])
S_227_err = np.array(tbdata['err_'+type_flux+'_flux_20']) + S_227*0.025

S_1400 = np.array(tbdata['S1400MHz'])
S_1400_err = S_1400*0.1
S_843 = np.array(tbdata['S843MHz'])
S_843_err = S_843*0.1
S_178 = np.array(tbdata['S178MHz'])
S_178_err = S_178*0.2
S_408 = np.array(tbdata['S408MHz'])
S_408_err = S_408*0.1
S_5000 = np.array(tbdata['S5000MHz'])
S_5000_err = S_5000*0.1
S_2700 = np.array(tbdata['S2700MHz'])
S_2700_err = S_2700*0.1
Name = np.array(tbdata['Name'])
RA = np.array(tbdata['_RAJ2000'])
Dec = np.array(tbdata['_DEJ2000'])
LAS = np.array(tbdata['LAS'])

freq = np.array([76,84,92,99,107,115,123,130,143,150,158,166,174,181,189,197,204,212,219,227,408,843,1400,2700,5000])
flux_mwa = np.vstack((S_076,S_084,S_092,S_099,S_107,S_115,S_123,S_130,S_143,
    S_150,S_158,S_166,S_174,S_181,S_189,S_197,S_204,S_212,S_219,S_227))
# flux_mwa = flux_mwa * zero[:,np.newaxis]
flux  = np.vstack((flux_mwa,S_408,S_843,S_1400,S_2700,S_5000))
flux_err = np.vstack((S_076_err,S_084_err,S_092_err,S_099_err,S_107_err,S_115_err,S_123_err,S_130_err,S_143_err,
    S_150_err,S_158_err,S_166_err,S_174_err,S_181_err,S_189_err,S_197_err,S_204_err,S_212_err,S_219_err,S_227_err,S_408_err,S_843_err,S_1400_err,S_2700_err,S_5000_err))

# Model fits

def powlaw(freq,a,alpha): # defining powlaw as S = a*nu^-alpha. Important to have x value first in definition of function.
    return a*(freq**(-alpha))

def singinhomobremss(freq,S_norm,alpha,p,freq_peak): # Single inhomogeneous free-free emission model    
    return S_norm*(p+1)*((freq/freq_peak)**(2.1*(p+1)-alpha))*special.gammainc((p+1),((freq/freq_peak)**(-2.1)))*special.gamma(p+1)

# Defining plotting routine.

print 'Finished reading in master catalogue'

cdict_models = {'singhomobremss':'red',
        'singhomobremsscurve':'maroon',
        'singhomobremssbreak': 'orangered',
        'singinhomobremss':'skyblue',
        'singinhomobremsscurve':'#4682b4',
        'doubhomobremss':'saddlebrown',
        'doubhomobremsscurve':'dodgerblue',
        'doubhomobremssbreak':'olive',
        'doubhomobremssbreak':'DarkGoldenRod',
        'singSSA':'orchid',
        'singSSAcurve':'darkmagenta',
        'singSSAbreak':'indigo',
        'doubSSA':'navy',
        'doubSSAcurve':'sienna',
        'doubSSAbreak':'black',
        'powlaw': 'DarkOrange',
        'powlawbreak':'Chocolate',
        'internalbremss':'MediumSeaGreen',
        'curve':'gray'
            } 

def sed(models,paras,freq,flux,flux_err, title = "No title provided.", 
        grid = False, freq_labels = False, log = True, bayes = False, resid = True, savefig=False):
    
    # Ensuring that freq and flux are approability matched up.
    ind = np.argsort(freq)
    freq = freq[ind]
    flux = flux[ind]
    flux_err = flux_err[ind]
    
    if resid == True:
        gs = plt.GridSpec(2,1, height_ratios = [3,1], hspace = 0)
        ax = plt.subplot(gs[0])
        ax1 = plt.subplot(gs[1])
        ax1.set_xlabel('Frequency (MHz)', fontsize = 15)
        ax1.set_ylabel(r'$\chi$', fontsize = 15)
    else:
        fig = plt.figure()
        ax = fig.gca()

    freq_cont = np.array(range(int(min(freq)-0.1*min(freq)),int(max(freq)+0.1*max(freq))))
    ax.set_xlim(min(freq_cont), max(freq_cont))
    ax.set_ylim(min(flux)-0.1*min(flux), max(flux)+0.2*max(flux))
    ax.set_xlabel('Frequency (MHz)', fontsize = 15)
    ax.set_ylabel('Flux Density (Jy)', fontsize = 15)
    ax.set_title(title, fontsize = 15)
    
    if freq_labels == True:
        
        for i in range(len(freq)):
            if freq[i] < 230. and freq[i] > 75.:
                ax.errorbar(freq[i], flux[i], flux_err[i], marker = '.', color = 'crimson', linestyle='none', label = 'GLEAM')
            else:
                ax.errorbar(freq[i], flux[i], flux_err[i], marker = '.', color = 'darkgreen', linestyle='none', label = 'Data')
    else:   
        ax.errorbar(freq, flux, flux_err, marker = '.', color = 'darkgreen', linestyle='none', label = 'Data')
    
    try:
        tt = len(models)
    except TypeError:
        tt = 1
        models = [models]
        paras = [paras]

    for i in range(tt):

        # Defining colours for models to make it easy to tell the difference
        try:
            color = cdict_models[models[i].__name__] # In case none of the models are listed here.        
        except KeyError:
            print 'Model is not in colour dictionary. Defaulting to dark orange.'
            color = 'DarkOrange'

        ax.plot(freq_cont, models[i](freq_cont, *paras[i]), color = color, linestyle='-', label="Best "+models[i].__name__+" fit to data.")
        
        if resid == True:
            model_points = models[i](freq,*paras[i])
            residuals = flux-model_points
            chi_sing = residuals/flux_err
            chi_sing_err = np.ones(len(freq)) # Chi errors are 1.
            # ax1.errorbar(freq,residuals,flux_err,color = color, linestyle='none',marker = '.')
            ax1.errorbar(freq,chi_sing,chi_sing_err,color = color, linestyle='none',marker = '.')
            compx = np.linspace(min(freq)-0.1*min(freq),max(freq)+0.1*max(freq))
            compy = np.zeros(len(compx))
            ax1.plot(compx,compy,linestyle = '--',color = 'gray',linewidth = 2)
            ax1.set_xlim(min(freq_cont), max(freq_cont))
            # ax1.set_ylim(min(chi_sing)-0.2*min(chi_sing), max(chi_sing)+0.2*max(chi_sing))

        # Elimanating doubled up legend values.
        handles, labels = ax.get_legend_handles_labels()
        by_label = OrderedDict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(),loc='upper right', fontsize=10)
        
        if log == True:
            ax.set_xscale('log')
            ax.set_yscale('log')
            
            # Making sure minor ticks are marked properly.

            def ticks_format(value, index):
                """
                get the value and returns the value as:
                   integer: [0,99]
                   1 digit float: [0.1, 0.99]
                   n*10^m: otherwise
                To have all the number of the same size they are all returned as latex strings
                """
                exp = np.floor(np.log10(value))
                base = value/10**exp
                if exp == 0 or exp == 1:   
                    return '${0:d}$'.format(int(value))
                if exp == -1:
                    return '${0:.1f}$'.format(value)
                else:
                    return '${0:d}\\times10^{{{1:d}}}$'.format(int(base), int(exp))

            # subs = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0] # ticks to show per decade
            # ax.xaxis.set_minor_locator(ticker.LogLocator(subs=subs)) #set the ticks position
            # ax.xaxis.set_major_formatter(ticker.NullFormatter())   # remove the major ticks
            # ax.xaxis.set_minor_formatter(ticker.FuncFormatter(ticks_format))
            # a = ax.get_xticks(minor=true).tolist()
            # ax.set_xticklabels(a)
            # ax.xaxis.get_ticklabels()[7] = ""
            # ax.xaxis.get_ticklabels()[8] = ""
            # xticks = ax.xaxis.get_minor_locator()
            # print xticks
            # ax.xaxis.get_ticklabels(), visible=False)
            # xticks[0].label1.set_visible(False)
            # ax.get_xaxis().set_visible(False)
            # ax.yaxis.set_minor_locator(ticker.LogLocator(subs=subs))
            # ax.yaxis.set_major_formatter(ticker.NullFormatter())   # remove the major ticks
            # ax.yaxis.set_minor_formatter(ticker.FuncFormatter(ticks_format))
            # ax.tick_params(axis='both',which='both',labelsize=14)
            
            subsx = [1.0, 2.0, 3.0, 5.0, 7.0] # ticks to show per decade
            subsy = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0] # ticks to show per decade
            ax.xaxis.set_minor_locator(ticker.LogLocator(subs=subsx)) #set the ticks position
            ax.xaxis.set_major_formatter(ticker.NullFormatter())   # remove the major ticks
            ax.xaxis.set_minor_formatter(ticker.FuncFormatter(ticks_format))
            ax.yaxis.set_minor_locator(ticker.LogLocator(subs=subsy))
            ax.yaxis.set_major_formatter(ticker.NullFormatter())   # remove the major ticks
            ax.yaxis.set_minor_formatter(ticker.FuncFormatter(ticks_format))
            ax.tick_params(axis='both',which='both',labelsize=12)

            if resid == True:
                ax.set_xticklabels('',minor = True)
                ax.set_xlabel('')
                ax1.set_xscale('log')
                ax1.xaxis.set_minor_locator(ticker.LogLocator(subs=subsx)) #set the ticks position
                ax1.xaxis.set_major_formatter(ticker.NullFormatter())   # remove the major ticks
                ax1.xaxis.set_minor_formatter(ticker.FuncFormatter(ticks_format))
                ax1.tick_params(axis='both',which='both',labelsize=12)

    if bayes == True:
        fig2 = plt.figure(2,figsize=(10, 10))
        
        for j in range(ndim):
            ax3 = fig.add_subplot(ndim,1,j+1)
            ax3.plot(np.array([sampler.chain[:,i,j] for i in range(nsteps)]),"k", alpha = 0.3)
            if userinputbayes == 'y':
                ax3.set_ylabel((r'$S_{norm}$',r'$\alpha$',r'$\nu_{peak}$',r'$\lnf$')[j], fontsize = 15)
            else:
                ax3.set_ylabel((r'$S_{norm}$',r'$\alpha$',r'$\nu_{peak}$')[j], fontsize = 15)

    if grid == True:
        ax.grid(which='both')
        if resid == True:
            ax1.grid(axis = 'x',which = 'both')

    if savefig == True:
        # Make a figures directory if there does not exist one and save the figures there.
        if title == "No title provided.":
            for i in plt.get_fignums():
                if i == 0:
                    print "Title names not provided. Graphs will be saved with figure numbers."
                title = 'Figure'+ str(plt.get_fignums()[-1])
        if not os.path.exists(os.getcwd()+'crossmatching/ms4/figures'):
            os.makedirs(os.getcwd()+'crossmatching/ms4/figures')
            print 'Creating directory ', os.getcwd()+'crossmatching/ms4/figures and saving figures in png format with title names.'
        plt.savefig('crossmatching/ms4/figures/'+title+'.png')
    plt.show()

alpha, alpha_err, redchisq_pow, redchisq_curve = [np.zeros(np.shape(flux[1])[0]) for dummy in range(4)]
cssind, ussind, gpsind = [],[],[]

def redchisq(ydata,ymod,sd,deg):
    
    chisq=np.sum(((ydata-ymod)/sd)**2)

    nu=ydata.size-1-deg

    return [chisq, chisq/nu]

for i in range(np.shape(flux[1])[0]): #[230] is pks0008-42

    fluxposind = np.where(flux[:,i] > 0)
    fluxplot = flux[:,i][fluxposind]
    freqplot = freq[fluxposind]
    flux_errplot = flux_err[:,i][fluxposind]

    peakfreq = freqplot[np.where(fluxplot == max(fluxplot))]
    peakflux = max(fluxplot)
    p0curve = [peakflux, peakfreq, 0.5, -0.7]
    p0pow = [peakflux,0.7]
    p0singinhomobremss = [peakflux, 0.5, -0.5, peakfreq]

    if len(fluxplot) > 3.:
        
        try:
            poptpowlaw, pcovpowlaw = opt.curve_fit(powlaw, freqplot, fluxplot, p0 = p0pow, sigma = flux_errplot, maxfev = 10000)
            redchisq_pow[i] = redchisq(fluxplot,powlaw(freqplot,*poptpowlaw),flux_errplot,2)[1]
            alpha[i]=poptpowlaw[1]
            alpha_err[i] = np.sqrt(pcovpowlaw[1][1])

            if alpha[i] > 0.5 and alpha[i] < 1: #Index has to be accurate as well.
                print 'Storing as a CSS source.'
                cssind.append(i)
            elif alpha[i] > 0.9: #Index has to be accurate as well.
                print 'Storing as a USS source.'
                ussind.append(i)
        except (RuntimeError): # If curve fit can not find a good fit, skip the source.    
            print 'Curve_fit could not fit powerlaw.'
        
        try:
            poptsinginhomobremss, pcovsinginhomobremss = opt.curve_fit(singinhomobremss, freqplot, fluxplot, p0 = p0singinhomobremss, sigma = flux_errplot, maxfev = 10000)
            redchisq_curve[i] = redchisq(fluxplot,singinhomobremss(freqplot,*poptsinginhomobremss),flux_errplot,4)[1]
            # print redchisq(fluxplot,gpscssmodels.singinhomobremss(freqplot,*poptsinginhomobremss),flux_errplot,4)
            if redchisq_curve[i] < redchisq_pow[i] and redchisq_curve[i] < 10. and redchisq_curve[i] > 0.:
                print 'Storing as a GPS source.'
                gpsind.append(i)
        except (RuntimeError):
            print 'Curve_fit could not find good inhomo fit.'

        if redchisq_curve[i] < 10. and redchisq_curve[i] > 0.:
            # userinput = raw_input("Hit enter if wanting plot of source, ortherwise hit s to skip:") #plotting sources as we go.
            # if userinput == '' :
            sed([powlaw,singinhomobremss],[poptpowlaw,poptsinginhomobremss],freqplot,fluxplot,flux_errplot, freq_labels = True, savefig = True, title = Name[i] + ' LAS = '+str(LAS[i]) )#+r' $\alpha$ = '+str(round(alpha[i],3))+r' Powlaw $ \chi_{\rm{red}}$  = '+str(round(redchisq_pow[i],2))+r' Inhomobremss $ \chi_{\rm{red}}$  = '+str(round(redchisq_curve[i],2)))
        elif redchisq_pow[i] > 0.:
            # userinput = raw_input("Hit enter if wanting plot of source, ortherwise hit s to skip:") #plotting sources as we go.
            # if userinput == '' :
            sed(powlaw,poptpowlaw,freqplot,fluxplot,flux_errplot, freq_labels = True, savefig = True, title = Name[i] + ' LAS = '+str(LAS[i])  )#+r' $\alpha$ = '+str(round(alpha[i],3))+r' Powlaw $ \chi_{\rm{red}}$  = '+str(round(redchisq_pow[i],2)))


# for i in gpsind:
#     fluxposind = np.where(flux[:,i] > 0)
#     fluxplot = flux[:,i][fluxposind]
#     freqplot = freq[fluxposind]
#     flux_errplot = flux_err[:,i][fluxposind]

#     peakfreq = freqplot[np.where(fluxplot == max(fluxplot))]
#     peakflux = max(fluxplot)
#     p0pow = [peakflux,0.7]
#     p0singinhomobremss = [peakflux, 0.5, -0.5, peakfreq]

#     poptpowlaw, pcovpowlaw = opt.curve_fit(gpscssmodels.powlaw, freqplot, fluxplot, p0 = p0pow, sigma = flux_errplot, maxfev = 10000)
#     poptsinginhomobremss, pcovsinginhomobremss = opt.curve_fit(gpscssmodels.singinhomobremss, freqplot, fluxplot, p0 = p0singinhomobremss, sigma = flux_errplot, maxfev = 10000)

#     userinput = raw_input("Hit enter if wanting plot of source, ortherwise hit s to skip:") #plotting sources as we go.
#     if userinput == '' :
#         sed([gpscssmodels.powlaw,gpscssmodels.singinhomobremss],[poptpowlaw,poptsinginhomobremss],freqplot,fluxplot,flux_errplot, freq_labels = True, savefig = False, title = MWACS_name[i] +r' $\alpha$ = '+str(round(alpha[i],3))+r' Powlaw $ \chi_{\rm{red}}$  = '+str(round(redchisq_pow[i],2))+r' Inhomobremss $ \chi_{\rm{red}}$  = '+str(round(redchisq_curve[i],2)))

# col1 = fits.Column(name='mwacs_name', format = '22A', array = MWACS_name[gpsind])
# col2 = fits.Column(name='RA_MWA', format = 'E', array = RA[gpsind])
# col3 = fits.Column(name='Dec_MWA', format = 'E', array = Dec[gpsind])

# cols = fits.ColDefs([col1, col2, col3])
# tbhdu = fits.new_table(cols)  
# print "#----------------------------------------------------------#"
# print 'Saving to a fits file.'  
# tbhdu.writeto('gpssrc_pos.fits', clobber = True)

# Plotting distribution of spectral indicies.
# bins = 9

# # (mu_fit, sigma_fit) = stats.norm.fit(alpha)
# alpha.sort()
# # gauss = mlab.normpdf(alpha, mu_fit, sigma_fit)

# # Note that the normed flag in the hist command normalises the histogram into a pdf. This means the integral of the histogram is one, not the sum of the bins.

# plt.figure(1)
# plt.clf()
# plt.hist(alpha, bins, histtype = 'step', color = 'deepskyblue',linewidth = 2, label = r'$\alpha$ '+'with all points.') #alpha = 0.5)
# # plt.plot(alpha, gauss, color = 'deepskyblue', linestyle= '--', linewidth = 2)
# plt.legend(loc='upper right') # make a legend in the best location
# plt.xlabel(r'$\alpha$', fontsize = '18')
# plt.ylabel('Number of Galaxies')
# plt.show()

# Plotting the position of these sources in the image plane using Aplpy.

# fig = aplpy.FITSFigure('/Users/Jcal/PhD/MWA/Commissioning/images/myimage.fits')
# fig = aplpy.FITSFigure('/Users/Jcal/PhD/MWA/Commissioning/images/C102_141_rescale.fits',auto_refresh=False)
# fig.recentre(33.23, 55.33, width=0.3, height=0.2)
# fig.show_grayscale()







