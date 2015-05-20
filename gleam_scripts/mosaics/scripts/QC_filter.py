#! /usr/bin/env python

__author__ = "PaulHancock"

import sys
#sys.path.insert(1,'/home/hancock/alpha/Aegean')
import numpy as np
from AegeanTools import catalogs, flags
from astropy.coordinates import SkyCoord
import astropy.units as u

def load(filename):
    print "load",filename
    table = catalogs.load_table(filename)
    return table

def save(table,filename):
    print "save",filename
    catalogs.save_catalog(filename,catalogs.table_to_source_list(table))

def filter_RADEC(table):
    print "RADEC filter"
    ramin,ramax = 0,360
    decmin,decmax = -73,20
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


def filter_region(table,region):
    """
    Return only sources that are within the given region.
    """
    return table

if __name__ == '__main__':
    infile,outfile = sys.argv[-2]
    #table = load('test.vot')
    #table = load('Week2_223-231MHz_comp.vot')
    table = load(infile)
    table = filter_RADEC(table)
    table = filter_GalacticPlane(table)
    table = filter_intpeak(table)
    save(table,outfile)
