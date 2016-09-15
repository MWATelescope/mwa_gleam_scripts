#!/usr/bin/env python

import numpy as np

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
parser.add_option('--plot',action="store_true",dest="make_plots",default=False,
                  help="Make fit plots? (default = False)")
parser.add_option('--rescale',action="store_true",dest="do_rescale",default=False,
                  help="Generate rescaled fits files? (default = False)")
parser.add_option('--order',dest="poly_order",default=5,type=int,
                  help="Set the order of the polynomial fit. (default = 5)")
parser.add_option('--write',action="store_true",dest="write_coefficients",default=False,
                    help="Write coefficients to file? (default = False)")
(options, args) = parser.parse_args()

tables = sorted(glob.glob('*_XY*_comp.vot'))

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

    figsize=(20,10)

    # Roughly 2:1 columns to rows
    subplot_cols=np.round(np.sqrt(len(tables))*1.4)
    subplot_rows=np.round(np.sqrt(len(tables))/1.4)

    if ((subplot_cols*subplot_rows)<len(tables)):
        if (subplot_cols<subplot_rows):
            subplot_cols+=1
        else:
            subplot_rows+=1

    plotnum=1

    fitplot=pyplot.figure(figsize=figsize)

for tablefile in tables:

    input_root=tablefile.replace("_comp.vot","")

    title=tablefile.split('_')[1]+'_'+tablefile.split('_')[2]
    table = parse_single_table(tablefile)
    data = table.array

    x=data['dec_X']
    y=data['peak_flux_Y']/data['peak_flux_X']
    w=data['peak_flux_X']/data['local_rms_X']

    N=len(data['dec_X'])

    P,res,rank,sv,cond = np.ma.polyfit(np.ma.array(x),np.ma.array(y),options.poly_order,full=True,w=w)
    fitmodel = np.poly1d(P)
# Remove outliers
    modsub = np.abs(y - fitmodel(x))
    indices = np.where(modsub<0.2)

    P,res,rank,sv,cond = np.ma.polyfit(np.ma.array(x[indices]),np.ma.array(y[indices]),options.poly_order,full=True,w=w[indices])
    fitmodel = np.poly1d(P)


    print "fit parameters:"
    print P
# Re-sort by S/N so that high S/N points are plotted over the top of low S/N points

    if options.make_plots:
        x=[X for (W,X) in sorted(zip(w,x))]
        y=[Y for (W,Y) in sorted(zip(w,y))]
        w=sorted(w)

        SNR=np.log10(w)
    #    print "SNR RANGE"
    #    print min(SNR),max(SNR)
    #    print min(w),max(w)
        ax = fitplot.add_subplot(subplot_rows,subplot_cols,plotnum)
        ax.set_title(title,fontsize=10)
        ax.scatter(x,y,marker='+',c=SNR,cmap=pyplot.cm.Greys)

        ax.plot(data['dec_X'],fitmodel(data['dec_X']),'.',ms=1)

    # Where the S/N is at least 30, find the min and max X:Y ratios, so the plots look good
        maw=np.ma.masked_less(w,30)
        may=np.ma.masked_array(y,mask=np.ma.getmask(maw))
        ax.set_ylim([np.ma.min(may),np.ma.max(may)])

        plotnum+=1

    if options.do_rescale:
        Xfits=re.sub('_XY_r','_XX_r',tablefile)
        Xfits=re.sub('_comp.vot','.fits',Xfits)
        newXfits=re.sub('.0.fits','.0_resc.fits',Xfits)

        if os.path.isfile(newXfits):
            os.remove(newXfits)

    # Modify the XX fits file to produce a new version
    # XXcorr=a*(Dec)^3 + b*(Dec)^2 + c*Dec + d

        hdu_in=fits.open(Xfits)
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
        XXcorr=np.zeros(dec.shape)
        for i in range(0,options.poly_order+1):
            XXcorr+=P[i]*pow(dec,options.poly_order-i)
#        XXcorr=(P[0]*pow(dec,3)+P[1]*pow(dec,2)+P[2]*(dec)+P[3])
        reshapedXXcorr=XXcorr.reshape(hdu_in[0].data.shape[0],hdu_in[0].data.shape[1])
        hdu_in[0].data=np.array(reshapedXXcorr*hdu_in[0].data,dtype=np.float32)
        hdu_in.writeto(newXfits)
        hdu_in.close()

if options.write_coefficients:
    outcoeff=input_root+'_xxyy_coefficients.fits'
    print "#----------------------------------------------------------#"
    print 'Saving correction to '+outcoeff

    fit_name = ['quintic']
    col1 = fits.Column(name='z', format = 'E', array = [P[5]])
    col2 = fits.Column(name='y', format = 'E', array = [P[4]])
    col3 = fits.Column(name='x', format = 'E', array = [P[3]])
    col4 = fits.Column(name='w', format = 'E', array = [P[2]])
    col5 = fits.Column(name='v', format = 'E', array = [P[1]])
    col6 = fits.Column(name='u', format = 'E', array = [P[0]])
#    if (Dec_strip == -26.0 or Dec_strip == -26.7 or Dec_strip == -27.0):
#        col5 = fits.Column(name='e', format = 'E', array = [polycoeffs[4]])
#        cols = fits.ColDefs([col1, col2, col3, col4, col5])
#    else:
    cols = fits.ColDefs([col1, col2, col3, col4, col5, col6])
    tbhdu = fits.new_table(cols)
    tbhdu.writeto(outcoeff, clobber = True)


#fitplot.show()
#fitplot.subplots_adjust(left=sbplt_pad_left, bottom=sbplt_pad_bottom, right=sbplt_pad_right, top=sbplt_pad_top, wspace=sbplt_pad_wspace, hspace=sbplt_pad_hspace)
if options.make_plots:
    outpng=input_root+"_"+"xxyy_int.png"
    fitplot.savefig(outpng,pad_inches=0.0,bbox_inches='tight')
