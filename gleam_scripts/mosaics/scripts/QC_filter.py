#!/usr/bin/env python

__author__ = "PaulHancock"

import os
import re
import sys
# GammaCrucis
sys.path.insert(1,'/home/hancock/alpha/Aegean') 
# Galaxy
sys.path.insert(1,os.environ['HOME']+'/bin/')
if 'MWA_CODE_BASE' in os.environ:
    mwa_code_base=os.environ['MWA_CODE_BASE']
    sys.path.insert(1,mwa_code_base+'/MWA_Tools/gleam_scripts/mosaics/scripts/')
    sys.path.insert(1,mwa_code_base+'/Aegean/')

import numpy as np
from AegeanTools import catalogs, flags
from AegeanTools.regions import Region
from astropy.coordinates import SkyCoord, Angle
import astropy.units as u
try:
    import cPickle as pickle
except ImportError:
    import pickle

from optparse import OptionParser

import logging
def load(filename):
    print "load", filename
    table = catalogs.load_table(filename)
    return table

def save(table,filename):
    print "save", filename
    if os.path.exists(filename):
        os.remove(filename)
    table.write(filename, format='votable')


def filter_RADEC(table, week):
    """
    Select only regions within the table that are known to be 'good', or at least not bad.
    """
    # hard coded ra/dec filter based on week.
    # From Natasha's table on the Google drive.
    print "RADEC filter"
    if week==1:
        band1 =                       (table['dec']<-30)  & (table['ra']>=21*15) 
        band2 = (table['dec']>=-30) & (table['dec']<0)    & (table['ra']>=20.5*15)
        good = np.where(band1 | band2)
    elif week==2:
        good = np.where( (table['ra']<8*15) & (table['dec']<30) )
    elif week==3:
        band1 =                       (table['dec']<-30)& (table['ra']>8*15)  & (table['ra']<13.5*15)
        band2 = (table['dec']>=-30) & (table['dec']<0)  & (table['ra']>=8*15) & (table['ra']<15.5*15)
        band3 = (table['dec']>=0)  & (table['dec']<30)  & (table['ra']>=8*15) & (table['ra']<14.5*15)
        good = np.where(band1 | band2 | band3)
    elif week==4:
        band1 =                      (table['dec']<-30)  & (table['ra']>=13.5*15) & (table['ra']<21*15)
        band2 = (table['dec']>=-30) & (table['dec']<0)   & (table['ra']>=15.5*15) & (table['ra']<20.5*15)
        band3 = (table['dec']>=0)   & (table['dec']<30)  & (table['ra']>=14.5*15) & (table['ra']<22*15)
        good = np.where(band1 | band2 | band3)
    elif week==5:
        return table
    elif week==6:
        band1 = (table['dec']<-2) & (table['dec']>-48) 
        band2 = (table['ra']>310) | (table['ra']<76)
        good = np.where(band1 & band2)
    else:
        print "bad week"
        sys.exit(1)
    return table[good]


def filter_GalacticPlane(table):
    """
    Filter out sources that have |b|<10\deg, consistent with the SUMSS/MGPS-2 division
    """
    print "filtering Galactic plane"
    bmax = 10
    b = abs(SkyCoord(table['ra']*u.deg, table['dec']*u.deg,frame="icrs").galactic.b.degree)
    good = np.where(b>=bmax)
    return  table[good]


def filter_aliases(table, week=None):
    """
    Remove the few pesky sources that are known to be aliases of other sources
    """
    if week is None:
        print "no week supplied - not filtering aliases"
        return table
    print "filtering aliased sources"
    # read lines from files
    if week==3:
        f = "Week3_CenA_ghosts.reg"
    elif week==4:
        f = "Week4_HerA_ghost.reg"
    else:
        print "there are no known aliased sources for week ",week
        return table
    if not os.path.exists(f):
        if os.path.exists(mwa_code_base+"/MWA_Tools/gleam_scripts/mosaics/scripts/"+f):
            f = mwa_code_base+"/MWA_Tools/gleam_scripts/mosaics/scripts/"+f
        else:
            print "cannot find ", f
            sys.exit(1)
    lines = (a for a in open(f).readlines() if a.startswith('ellipse'))
    # convert lines into ra,dec,a,b,pa
    words = [re.split('[(,\s)]', line) for line in lines]
    pos = [ SkyCoord(w[1], w[2], unit=(u.hourangle,u.degree)) for w in words]
    ra = np.array([p.ra.degree for p in pos])
    dec = np.array([p.dec.degree for p in pos])
    shape = [ map(lambda x: float(x.replace('"','')), w[3:6]) for w in words]
    a,b,pa = map(np.array,zip(*shape))
    # convert from ds9 to 'true' position angle
    pa += 90
    a /=3600.
    b /=3600.
    # all params are now in degrees
    kill_list=[]
    # loops for now
    for i in range(len(ra)):
        # define a box that is larger than needed
        dmin = dec[i] - 3*a[i]
        dmax = dec[i] + 3*a[i]
        rmin = ra[i] - 3*a[i]
        rmax = ra[i]  + 3*a[i]
        # Select all sources within this box
        mask = np.where( (table['dec']<dmax) & (table['dec']>dmin) & (table['ra']>rmin) & (table['ra']<rmax) )[0]
        if len(mask) < 1:
            continue
        # create a catalog of this subset
        cat = SkyCoord(table[mask]['ra'],table[mask]['dec'], unit=(u.degree, u.degree))
        # define our reference position and find all sources that are within the error ellipse
        p = pos[i]
        # yay for vectorized functions in astropy
        offset = p.separation(cat).degree
        pa_off = p.position_angle(cat).radian
        pa_diff = pa_off - np.radians(pa[i])
        radius = a[i]*b[i] / np.sqrt( (b[i]*np.cos(pa_diff))**2 + (a[i]*np.sin(pa_diff))**2)
        # print 'radius', radius
        # print 'offset', offset
        to_remove = np.where(radius>=offset)[0]
        # print 'sources within box', mask
        # print 'marked for removal',to_remove,
        # print mask[to_remove]
        if len(to_remove)<1:
            continue
        # save the index of the sources that are within the error ellipse
        kill_list.extend(mask[to_remove])
    print "table has ", len(table), "sources"
    print "there are ", len(kill_list), "sources to remove"
    table.remove_rows(kill_list)
    print "there are now ", len(table), "sources left in the table"
    return table

def filter_flags(table):
    """

    """
    return table


def filter_residual(table):
    """
    """

    return table


def filter_rms(table):
    """
    Discard sources that have a local rms >0.5 since they are in dodgy ares of the sky
    """
    print "filtering local_rms"
    good = np.where(table['local_rms']<0.5)
    return table[good]

def filter_intpeak(table):
    """
    Discard sources that have int_flux/peak_flux > 10.
    """
    print "filtering int/peak"
    good = np.where( table['int_flux']/table['peak_flux']<10)
    return table[good]

def filter_cena_reflection(table):
    """
    """
    bad = (table['ra'] > (13+7./60)*15) & (table['ra'] < (13+53./60)*15) & (table['dec']>20) & (table['dec']<30)
    good = np.bitwise_not(bad)
    return table[good]


def adjust_errors(table):
    """
    A scant few columns have err==-1.
    Modify these errors to be equal to the value (ie 100% error)
    """
    # -1 error on fluxes -> 100% flux error
    cols = ["peak_flux", "int_flux"]
    err_cols = [ "err_"+a for a in cols]

    for v,e in zip(cols, err_cols):
        mask = np.where(table[e]<0)
        print v,e,len(mask[0])
        table[e][mask] = table[v][mask]
    
    # -1 error on ra/dec -> error is just semi-major axis.
    mask = np.where(table['err_ra']<0)
    table['err_ra'][mask] = table['a'][mask]

    mask = np.where(table['err_dec']<0)
    table['err_dec'][mask] = table['a'][mask]

def make_mim():
    """
    """
    srclist = {}
    for l in open('sources_to_clip.dat').readlines():
        if l.startswith('#'):
            continue
        name = l.split()[0]
        ra = ' '.join(l.split()[1:4])
        dec = ' '.join(l.split()[4:7])
        radius = float(l.split()[7])/60.
        pos = SkyCoord(Angle(ra,u.hour),Angle(dec,u.degree))
        srclist[name] = (pos.ra.degree,pos.dec.degree, radius)
    for k in srclist.keys():
        v = srclist[k]
        print 'MIMAS +c {0} {1} {2} -o {3}.mim'.format(v[0],v[1],v[2],k)
    everything = srclist.keys()
    print "MIMAS ",
    for e in everything:
        print "+r {0}.mim".format(e),
    print " -o all.mim"
    #print "MIMAS.py +c 0 -90 120 -o south.mim"
    #print "MIMAS.py +r south.mim -r all.mim -o masked.mim"
    #print "MIMAS.py --mim2fits masked.mim masked.fits"
    return


def filter_region(table,regionfile):
    """
    """
    print "Filtering from file {0}".format(regionfile)
    r = pickle.load(open(regionfile,'r'))
    print r.get_area()
    bad = r.sky_within(table['ra'],table['dec'],degin=True)
    good = np.bitwise_not(bad)
    return table[good]

if __name__=="__main__":
    logging.getLogger('Aegean')

    usage="Usage: %prog [options]\n"
    parser = OptionParser(usage=usage)
    parser.add_option('--input',dest="input",default=None,
      help="Input VO table to filter.")
    parser.add_option('--output',dest="output",default=None,
      help="Output VO table -- default is input_filter.vot")
    parser.add_option('--mimtable',dest="mimtable",default=None,
      help="MIMAS table to read in (please use MWA_Tools/gleam_scripts/mosaics/scripts/all.mim)")
    parser.add_option('--week', dest="week", default=None, type='int',
      help="Week number for custom filtering options")
    parser.add_option('--makemim',dest='make',default=False, action='store_true',
        help='Make a MIMAS file from sources_to_clip.dat')
    (options, args) = parser.parse_args()


    if options.make:
        make_mim()
        sys.exit(0)
    
    print options.input
    # Parse the input options
    if options.input is None:
        print "Error! Must specify an input file."
        sys.exit(1)
    elif not os.path.exists(options.input):
        print "File not found {0}".format(options.input)
        sys.exit(1)
    else:
        infile=options.input

    if options.output:
        outfile=options.output
    else:
        outfile=infile.replace(".vot","_filter.vot")

    if options.mimtable:
        mimtable=options.mimtable
    else:
        mimtable=mwa_code_base+"/MWA_Tools/gleam_scripts/mosaics/scripts/all.mim"

    # Run the filters we've defined
    table = load(infile)

    if options.week is None:
        print "No week supplied, not applying week-specific ra/dec cuts"
    else:
        table = filter_RADEC(table,options.week)
    table = filter_GalacticPlane(table)
    table = filter_intpeak(table)
    table = filter_region(table,mimtable)
    table = filter_aliases(table, options.week)
    table = filter_cena_reflection(table)
    adjust_errors(table)
    save(table, outfile)

