#! /usr/bin/env python

__author__ = "PaulHancock"

import os
import sys
# GammaCrucis
#sys.path.insert(1,'/home/hancock/alpha/Aegean') 
# Galaxy
home=os.environ['HOME']
sys.path.insert(1,home+'/bin/')
#mwa_code_base=os.environ['MWA_CODE_BASE']
#sys.path.insert(1,mwa_code_base+'MWA_Tools/gleam_scripts/mosaics/scripts/')

import numpy as np
from AegeanTools import catalogs, flags
from AegeanTools.regions import Region
from astropy.coordinates import SkyCoord, Angle
from astropy.io.votable import writeto as writetoVO
import astropy.units as u
try:
    import cPickle as pickle
except ImportError:
    import pickle

def load(filename):
    print "load",filename
    table = catalogs.load_table(filename)
    return table

def save(table,filename):
    print "save",filename
    writetoVO(table,filename)
    #catalogs.save_catalog(filename,catalogs.table_to_source_list(table))


def filter_RADEC(table):
    print "RADEC filter"
    ramin,ramax = 0,120
    decmin,decmax = -90,30
    good = []
    for i,row in enumerate(table):
        if ramin<=row['ra']<=ramax:
            if decmin<=row['dec']<decmax:
                good.append(i)
    return table[good]


def filter_GalacticPlane(table):
    """
    Filter out sources that have |b|<10\deg, consistent with the SUMSS/MGPS-2 division
    """
    print "filtering Galactic plane"
    bmax = 10
    good = []
    b = abs(SkyCoord(table['ra']*u.deg, table['dec']*u.deg,frame="icrs").galactic.b.degree)
    good = np.where(b>=bmax)
    return  table[good]


def filter_flags(table):
    """

    """
    return table


def filter_residual(table):
    """
    """

    return table


def filter_intpeak(table):
    """
    Discard sources that have int_flux/peak_flux > 10.
    """
    print "filtering int/peak"
    good = np.where( table['int_flux']/table['peak_flux']<10)
    return table[good]


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
        pos = SkyCoord(Angle(ra,u.hour),Angle(dec,u.degree))
        srclist[name] = (pos.ra.degree,pos.dec.degree)
    for k in srclist.keys():
        if k=='LMC':
            radius = 4
        elif k =='SMC':
            radius = 1.5
        else:
            radius = 5./60
        v = srclist[k]
        print 'MIMAS.py +c {0} {1} {2} -o {3}.mim'.format(v[0],v[1],radius,k)
    everything = srclist.keys()
    print "MIMAS.py ",
    for e in everything:
        print "+r {0}.mim".format(e),
    print " -o all.mim"
    print "MIMAS.py +r south.mim -r all.mim -o masked.mim"
    print "MIMAS.py --mim2fits masked.mim masked.fits"
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


if __name__ == '__main__':
    #make_mim()
    #sys.exit()
    infile,outfile = sys.argv[-2:]
    try:
        mimtable=sys.argv[1:][2]
    except:
        mimtable=mwa_code_base+"gleam_scripts/mosaics/scripts/all.mim"
    table = load(infile)
    table = filter_RADEC(table)
    table = filter_GalacticPlane(table)
    table = filter_intpeak(table)
    table = filter_region(table,mimtable)
    save(table,outfile)
