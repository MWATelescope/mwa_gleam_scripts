#!/usr/bin/env python

#image manipulation 
from scipy.interpolate import griddata

import numpy as np
import scipy
import scipy.stats
import math
import os, sys, re

import matplotlib as ml
ml.use('Agg') # So does not use display
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable

from astropy.io.votable import writeto as writetoVO
from astropy.table import Table, Column
from astropy.io.votable import parse_single_table
from astropy.io import fits

from optparse import OptionParser

usage="Usage: %prog [options]\n"
parser = OptionParser(usage=usage)
parser.add_option('--input',dest="input",default=None,
                  help="Input VO table to characterise.")
parser.add_option('--fitsfile',dest="fitsfile",default=None,
                  help="Corresponding fits file (default is to search for one based on filenames).")
parser.add_option('--gridsize',dest="gridsize",default=15.0,
                  help="Specify grid size in degrees (default = 15 deg)")
parser.add_option('--stepsize',dest="stepsize",default=1,
                  help="Specify step size in degrees (default = 1 deg)")
parser.add_option('--minsnr',dest="minsnr",default=10.0,type="float",
                  help="Minimum S/N ratio for sources used to fit PSF (default = 10 sigma)")
parser.add_option('--nomrc',action="store_false",dest="usemrc",default=True,
                  help="Don't use MRC (and VLSSr North of Dec 0) to select unresolved sources? (default = use ancillary catalogues.)")
parser.add_option('--noisolate',action="store_false",dest="isolate",default=True,
                  help="Don't exclude sources near other sources? (will exclude by default)")
parser.add_option('--noplot',action="store_false",dest="make_plots",default=True,
                  help="Turn off psf plots? (on by default)")
parser.add_option('--noresiduals',action="store_false",dest="residuals",default=True,
                  help="Turn off exclusion by residuals from elliptical fit? (on by default)")
parser.add_option('--initsize',dest="initsize",default=None,
                  help="Specify initial histogram bin size in degrees (default = don't specify, and no initial gridding will be performed (probably the better option))")
parser.add_option('--output',dest="output",default=None,
                  help="Output png file -- default is input_psf.png")
(options, args) = parser.parse_args()

# Parse the input options

if not os.path.exists(options.input):
    print "Error! Must specify an input file."
    sys.exit(1)
else:
    inputfile=options.input
    if options.fitsfile:
        fitsfile=options.fitsfile
    else:
        fitsfile=inputfile.replace('_comp.vot','.fits')
        if not os.path.exists(fitsfile):
            tempvar=inputfile.split("_")
            fitsfile=tempvar[0]+"_"+tempvar[1]+".fits"

if os.path.exists(fitsfile):
    print "Corresponding fits image found."
    dopsfout=True
    try:
        hdulist=fits.open(fitsfile)
        header=hdulist[0].header
        central_RA=header['CRVAL1']
        start_freq=(header['FREQ']/1e6)-(7.68/2)
    except:
        print "No frequency found in fitsheader; will estimate the frequency from the input filename."
        start_freq=int(re.search("[0-9]{3}",inputfile).group())
else:
    print "No corresponding fits image found; will estimate the frequency from the input filename."
    try:
        start_freq=int(re.search("[0-9]{3}",inputfile).group())
    except:
# Default is for 'white' image
        start_freq=170.
    print "No corresponding fits image found; will be unable to write PSF map."
    dopsfout=False

# Have to categorise the band by hand since the component catalogues know nothing about frequency
if start_freq < 96:
    fid_freq=(95+(7.68))
    amin=190
    amax=450
    bmin=170
    bmax=350
elif 96 < start_freq < 127:
    fid_freq=(126+(7.68))
    amin=150
    amax=350
    bmin=110
    bmax=250
elif 127 < start_freq < 163:
    fid_freq=(162+(7.68))
    amin=120
    amax=250
    bmin=90
    bmax=200
elif 163 < start_freq < 194:
    fid_freq=(193+(7.68))
    amin=100
    amax=230
    bmin=95
    bmax=170
elif 194 < start_freq < 231:
    fid_freq=(223+(7.68))
    amin=100
    amax=210
    bmin=80
    bmax=150

mid_freq=(start_freq+(7.68))
psf_ratio=np.sqrt(mid_freq/fid_freq)

if options.output:
    outputfile=options.output
    title=outputfile.replace(".png","")
else:
    outputfile=inputfile.replace("_comp.vot","_psf.png")
    title=inputfile.replace("_comp.vot","")

outputvot=inputfile.replace("_comp.vot","_psf.vot")

# Set up the filter parameters
gridsize=float(options.gridsize)
stepsize=float(options.stepsize)
rbins=scipy.arange(0.8,4.0,0.1)

# What parameters to fit (only first four will be plotted, rest will generate bonus fits files)
# Make sure you pick an Aegean-generated column unless you add a hook to interpret a non-Aegean column
param_names=["a","b","pa","int_peak","nsrc"]

# Function definitions

# For unwrapping RA values which bridge the meridian
def unwrap(x):
    if x>180:
        return x-360
    else:
        return x
vunwrap=np.vectorize(unwrap)

# For unwrapping phase values which bridge the -90/+90
def unphase(x):
    if x<0:
        return x+180
    else:
        return x
vunphase=np.vectorize(unphase)

def average_region(data,xmin,xmax,ymin,ymax,params):
    x=data['ra']
    y=data['dec']
    newmask=np.where( (x>=xmin) & (x<xmax) & (y>=ymin) & (y<ymax))
    weights=(data['peak_flux'][newmask]/data['local_rms'][newmask])*(data['peak_flux'][newmask]/data['residual_std'][newmask])
    vals=[]
    for param in params:
        docount=False
# Hooks for non-Aegean-column names
        if param=="int_peak":
            param_vals=data["int_flux"][newmask]/data["peak_flux"][newmask]
        elif param=="nsrc":
            param_vals=data["int_flux"][newmask]
            docount=True
        else: 
# Aegean column name
            param_vals=data[param][newmask]
        if len(param_vals)==0:
           vals.append(np.nan)
        else:
           if docount:
               vals.append(np.count_nonzero(param_vals))
           else:
               vals.append(np.average(param_vals,weights=weights))
    return vals

def maxind(data,bins,weights):
# Bin the data
    hist=np.histogram(data,bins=bins,weights=weights,density=True)
    np.argmax(hist[0])
# Grab the most populated bin, and the ones to either side
#    indices=np.where( (data>=bins[np.argmax(hist[0])-1]) & (data<bins[np.argmax(hist[0])+2]))
# Grab everything smaller than the next bin up from the most populated bin
    indices=np.where(data<bins[np.argmax(hist[0])+2])
    return indices

def locations(step_size,xmin,xmax,ymin,ymax):
    """
    Generator function to iterate over a grid of x,y coords
    operates only within the given bounds
    Returns:
    x,y,previous_x,previous_y
    """

    xvals = np.arange(xmin,xmax,step_size[0]).tolist()
    if xvals[-1]!=xmax:
        xvals.append(xmax)
    yvals = np.arange(ymin,ymax,step_size[1]).tolist()
    if yvals[-1]!=ymax:
        yvals.append(ymax)
    #initial data
    px,py=xvals[0],yvals[0]
    i=1
    for y in yvals:
        for x in xvals[::i]:
            yield x,y,px,py
            px,py=x,y
        i*=-1 #change x direction

def filter(data,params,gridsize,stepsize):

    x=data['ra']
    y=data['dec']
    minx=min(x)
    miny=min(y)
    maxx=max(x)
    maxy=max(y)
    nx=math.ceil((maxx-minx)/gridsize)
    ny=math.ceil((maxy-miny)/gridsize)

    def box(x,y):
        """
        calculate the boundaries of the box centered at x,y
        with size = box_size
        """
        x_min = max(minx,x-gridsize/2)
        x_max = min(maxx,x+gridsize/2)
        y_min = max(miny,y-gridsize/2)
        y_max = min(maxy,y+gridsize/2)
        return x_min,x_max,y_min,y_max

    xypoints = []
    param_values = []
    
    for x,y,_,_ in locations((stepsize,stepsize),minx,maxx,miny,maxy):
        x_min,x_max,y_min,y_max = box(x,y)
        param_values.append(average_region(data,x_min,x_max,y_min,y_max,params))
        xypoints.append((x,y))
    param_values=np.array(param_values)
    interpolated_params=[]
# Can make the stepsize here smaller to make it do more interpolation
    (gx,gy) = np.mgrid[minx:maxx+stepsize:stepsize,miny:maxy+stepsize:stepsize]
    for i,p in enumerate(params):
        interpolated_params.append(griddata(xypoints,param_values[:,i],(gx,gy),method='linear'))
    #print interpolated_params[-1][3:5,3:5]
    return interpolated_params

# End of function definitions

sparse=inputfile
# Read the VO table and start processing
if options.isolate:
    sparse=re.sub("_comp.vot","_isolated_comp.vot",inputfile)
    os.system('stilts tmatch1 matcher=sky values="ra dec" params=600 \
               action=keep0 in='+inputfile+' out='+sparse)

if options.usemrc:
    psfvot=re.sub("_comp.vot","_psf.vot",inputfile)
    catdir=os.environ['MWA_CODE_BASE']+'/MWA_Tools/catalogues'
    MRCvot=catdir+"/MRC.vot"
    VLSSrvot=catdir+"/VLSSr.vot"
# GLEAM: Get rid of crazy-bright sources, really super-extended sources, and sources with high residuals after fit
    os.system('stilts tpipe in='+sparse+' cmd=\'select ((local_rms<1.0)&&((int_flux/peak_flux)<2)&&((residual_std/peak_flux)<0.1))\' out=temp_crop.vot')
# MRC: get point like sources (MFLAG is blank)
    Mmatchvot=re.sub("_comp.vot","_MRC.vot",sparse)
    os.system('stilts tpipe in='+MRCvot+' cmd=\'select NULL_MFLAG\' cmd=\'addcol PA_MRC "0.0"\' out=mrc_temp.vot')
# Use only isolated sources
    os.system('stilts tmatch1 matcher=sky values="_RAJ2000 _DEJ2000" params=600 \
               action=keep0 in=mrc_temp.vot out=mrc_crop.vot')
# Match GLEAM with MRC
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1=mrc_crop.vot in2=temp_crop.vot out=temp_mrc_match.vot values1="_RAJ2000 _DEJ2000 2*e_RA2000 2*e_DE2000 PA_MRC" values2="ra dec 2*a 2*b pa" ofmt=votable')
# Keep only basic aegean headings
    os.system('stilts tpipe in=temp_mrc_match.vot cmd=\'keepcols "ra dec peak_flux err_peak_flux int_flux err_int_flux local_rms a err_a b err_b pa err_pa residual_std flags"\' out='+Mmatchvot)

# VLSSr: get point-like sources (a and b are < 86", same resolution as MRC); only sources North of Dec +20
    Vmatchvot=re.sub("_comp.vot","_VLSSr.vot",sparse)
    os.system('stilts tpipe in='+VLSSrvot+' cmd=\'select ((MajAx<.02389)&&(MinAx<0.02389)&&(_DEJ2000>0)) \' out=vlssr_temp.vot')
# Use only isolated sources
    os.system('stilts tmatch1 matcher=sky values="_RAJ2000 _DEJ2000" params=600 \
               action=keep0 in=vlssr_temp.vot out=vlssr_crop.vot')
# Match GLEAM with VLSSr
    os.system('stilts tmatch2 matcher=sky params=120 in1=vlssr_crop.vot in2=temp_crop.vot out=temp_vlssr_match.vot values1="_RAJ2000 _DEJ2000" values2="ra dec" ofmt=votable')
# Keep only basic aegean headings
    os.system('stilts tpipe in=temp_vlssr_match.vot cmd=\'keepcols "ra dec peak_flux err_peak_flux int_flux err_int_flux local_rms a err_a b err_b pa_2 err_pa residual_std flags"\' out='+Vmatchvot)
# Concatenate the MRC and VLSSr matched tables together
    os.system('stilts tcat in='+Mmatchvot+' in='+Vmatchvot+' out='+psfvot)

    os.remove('temp_crop.vot')
    os.remove('mrc_temp.vot')
    os.remove('mrc_crop.vot')
    os.remove('temp_mrc_match.vot')
    os.remove('vlssr_temp.vot')
    os.remove('vlssr_crop.vot')
    os.remove('temp_vlssr_match.vot')
    os.remove(Mmatchvot)
    os.remove(Vmatchvot)

    table = parse_single_table(psfvot)
    data = table.array
else:
    table = parse_single_table(sparse)
    data = table.array

x=data['ra']

# NB: this will break if your catalogue stretches all the way from RA0 to RA12 or RA12 to RA0
if min(x)<1. and max(x)>359.:
    data['ra']=vunwrap(data['ra'])

x=data['ra']
y=data['dec']
    
# Downselect to unresolved sources

mask=[]
if options.initsize:
    initsize=float(options.initsize)
    for gx in scipy.arange(min(x),max(x),initsize):
        for gy in scipy.arange(min(y),max(y),initsize):
    ## Filter out any sources where Aegean's flags weren't zero, and only use sources within the grid
            indices=np.where( (x>=gx) & (x<gx+initsize) & (y>=gy) & (y<gy+initsize) & (data['flags']==0) & ((data['peak_flux']/data['local_rms'])>=options.minsnr) )
            weights=(data['peak_flux'][indices]/data['local_rms'][indices])*(data['peak_flux']/data['residual_std'])
    ## Populate grid
            newindices=maxind(data['int_flux'][indices]/data['peak_flux'][indices],rbins,weights)
            mask.extend(indices[0][newindices])
else:
# Filter out any sources where Aegean's flags weren't zero
    indices=np.where((data['flags']==0) & ((data['peak_flux']/data['local_rms'])>=options.minsnr))
    if not options.usemrc:
        weights=data['peak_flux'][indices]/data['local_rms'][indices]
# Just remove bad sources, and assume that the PSF is uniform enough that I can just grab the lowest few bins
        newindices=maxind(data['int_flux'][indices]/data['peak_flux'][indices],rbins,weights)
        mask.extend(indices[0][newindices])
    else:
        mask.extend(indices[0])
    mask=np.array(mask)

# Run the filter to perform the boxcar smoothing
agrid=filter(data[mask],param_names,gridsize,stepsize)
    
#    np.save(savednumpyarray,agrid)
#    np.save(xpos,x[mask])
#    np.save(ypos,y[mask])
#    x=x[mask]
#    y=y[mask]

vot = Table(data[mask])
vot.description = "Sources selected for PSF calculation."
writetoVO(vot, outputvot)


# Plotting
if options.make_plots:
    fig,((ax1,ax2),(ax3,ax4)) = plt.subplots(nrows=2,ncols=2,figsize=(15, 15))
    extent=[max(x[mask]),min(x[mask]),min(y[mask]),max(y[mask])]

    # Major Axis
    ax1.set_title('major axis (arcsec)')
    im1=ax1.imshow(np.fliplr(np.flipud(agrid[0].transpose())),interpolation='none',extent=extent,aspect='auto',vmin=amin,vmax=amax)#,cmap="cubehelix")
    # Create divider for existing axes instance
    divider1 = make_axes_locatable(ax1)
    # Append axes to the right of ax1, with 10% width of ax1
    cax1 = divider1.append_axes("right", size="10%", pad=0.05)
    # Create colorbar in the appended axes
    # Tick locations can be set with the kwarg `ticks`
    # and the format of the ticklabels with kwarg `format`
    cbar1 = plt.colorbar(im1, cax=cax1)
    # Unset x-labels
    ax1.set_xticklabels([])
    ax1.set_ylabel('Declination (deg)')

    # Minor Axis
    ax2.set_title('minor axis (arcsec)')
    im2=ax2.imshow(np.fliplr(np.flipud(agrid[1].transpose())),interpolation='none',extent=extent,aspect='auto',vmin=bmin,vmax=bmax)#,cmap="cubehelix")
    divider2 = make_axes_locatable(ax2)
    cax2 = divider2.append_axes("right", size="10%", pad=0.05)
    cbar2 = plt.colorbar(im2, cax=cax2)
    ax2.set_xticklabels([])
    # Unset y-labels
    ax2.set_yticklabels([])

    # Position Angle
    ax3.set_title('position angle (deg)')
    im3=ax3.imshow(np.fliplr(np.flipud(agrid[2].transpose())),interpolation='none',extent=extent,aspect='auto',vmin=-90.0,vmax=90.0)#) #,vmin=min(rbins),vmax=max(rbins))#,cmap="cubehelix")
    divider3 = make_axes_locatable(ax3)
    cax3 = divider3.append_axes("right", size="10%", pad=0.05)
    cbar3 = plt.colorbar(im3, cax=cax3)
    ax3.set_ylabel('Declination (deg)')
    ax3.set_xlabel('RA (deg)')

    # Int / Peak
    ax4.set_title('int/peak')
    im4=ax4.imshow(np.fliplr(np.flipud(psf_ratio*agrid[3].transpose())),interpolation='none',extent=extent,aspect='auto',vmin=1.0,vmax=2.0)#,cmap=cmap2)
    divider4 = make_axes_locatable(ax4)
    cax4 = divider4.append_axes("right", size="10%", pad=0.05)
    cbar4 = plt.colorbar(im4, cax=cax4)
    ax4.set_yticklabels([])
    ax4.set_xlabel('RA (deg)')

    plt.savefig(outputfile)

# Create PSF maps

if dopsfout:
    param_indices=range(0,len(param_names))
    params=zip(param_indices,param_names)
    for i,param in params:
        outfitsfile=inputfile.replace('_comp.vot','_'+param+'.fits')
        if 'CDELT1' in header:
            header['CDELT1'] = stepsize
        elif 'CD1_1' in header:
            header['CD1_1'] = stepsize
        else:
            print "Error: Can't find CDELT1 or CD1_1"
        if 'CDELT2' in header:
            header['CDELT2'] = stepsize
        elif 'CD2_2' in header:
            header['CD2_2'] = stepsize
        else:
            print "Error: Can't find CDELT2 or CD2_2"
    # CRVAL2 needs to be zero in order for a plate caree (CAR) projection to resemble a Cartesian grid
        header['CRVAL2']=0.0
    # The pixel values where Dec is 0
        header['CRPIX2']=-min(y[mask])/stepsize
    # CRVAL1 should be in the middle of the image
        header['CRVAL1']=central_RA
        header['CRPIX1']=central_RA-min(x[mask])/stepsize

        header['CTYPE1']='RA---CAR'
        header['CTYPE2']='DEC--CAR'
        hdulist[0].data = agrid[i].transpose()
        hdulist[0].header = header
        hdulist.writeto(outfitsfile, clobber=True)

# param_names are [a,b,pa,...]
    print 'Making multi dimensional image'
    outfile = inputfile.replace('_comp.vot','_triple.fits')
    if 'CDELT1' in header:
        header['CDELT1'] = stepsize
    elif 'CD1_1' in header:
        header['CD1_1'] = stepsize
    else:
        print "Error: Can't find CDELT1 or CD1_1"
    if 'CDELT2' in header:
        header['CDELT2'] = stepsize
    elif 'CD2_2' in header:
        header['CD2_2'] = stepsize
    else:
        print "Error: Can't find CDELT2 or CD2_2"
# CRVAL2 needs to be zero in order for a plate caree (CAR) projection to resemble a Cartesian grid
    header['CRVAL2']=0.0
# The pixel values where Dec is 0
    header['CRPIX2']=-min(y[mask])/stepsize
# CRVAL1 should be in the middle of the image
    header['CRVAL1']=central_RA
    header['CRPIX1']=central_RA-min(x[mask])/stepsize
    header['CRPIX3']=0
    header['CTYPE1']='RA---CAR'
    header['CTYPE2']='DEC--CAR'
    header['CTYPE3']=('Beam',"0=a,1=b,2=pa (degrees)")
    newdata = np.array([ agrid[0].transpose()/3600 , agrid[1].transpose()/3600, agrid[2].transpose()])
    #newdata[np.where(np.bitwise_not(np.isfinite(newdata)))]=0
    hdulist[0].data = newdata
    hdulist[0].header = header
    hdulist.writeto(outfile, clobber=True)
