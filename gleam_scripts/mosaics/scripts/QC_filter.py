#!/usr/bin/env python

__author__ = "PaulHancock"

import os
import sys
# GammaCrucis
#sys.path.insert(1,'/home/hancock/alpha/Aegean') 
# Galaxy
home=os.environ['HOME']
sys.path.insert(1,home+'/bin/')
mwa_code_base=os.environ['MWA_CODE_BASE']
sys.path.insert(1,mwa_code_base+'/MWA_Tools/gleam_scripts/mosaics/scripts/')
sys.path.insert(1,mwa_code_base+'/new_version_Aegean/bin')

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

from optparse import OptionParser

usage="Usage: %prog [options]\n"
parser = OptionParser(usage=usage)
parser.add_option('--input',dest="input",default=None,
                  help="Input VO table to filter.")
parser.add_option('--output',dest="output",default=None,
                  help="Output VO table -- default is input_filter.vot")
parser.add_option('--mimtable',dest="mimtable",default=None,
                  help="MIMAS table to read in (default is MWA_Tools/gleam_scripts/mosaics/scripts/all.mim)")
parser.add_option('--minRA',dest="minRA",default=0.0,type="float",
                  help="Minimum RA to allow through, in degrees (default = 0)")
parser.add_option('--maxRA',dest="maxRA",default=360.0,type="float",
                  help="Maximum RA to allow through, in degrees (default = 360)")
parser.add_option('--minDec',dest="minDec",default=-90.0,type="float",
                  help="Minimum Dec to allow through, in degrees (default = -90)")
parser.add_option('--maxDec',dest="maxDec",default=35.0,type="float",
                  help="Maximum Dec to allow through, in degrees (default = 35)")
(options, args) = parser.parse_args()

# Parse the input options

if not os.path.exists(options.input):
    print "Error! Must specify an input file."
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

ramin, ramax, decmin, decmax = options.minRA, options.maxRA, options.minDec, options.maxDec

def load(filename):
    print "load",filename
    table = catalogs.load_table(filename)
    return table

def save(table,filename):
    print "save",filename
    writetoVO(table,filename)
    #catalogs.save_catalog(filename,catalogs.table_to_source_list(table))

def filter_RADEC(table,ramin,ramax,decmin,decmax):
    print "RADEC filter"
    good = []
    if ramin>ramax:
        for i,row in enumerate(table):
            if 0.0<=row['ra']<=ramin or ramax<=row['ra']<=360.0:
                if decmin<=row['dec']<decmax:
                    good.append(i)
    else:
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

# Run the filters we've defined

table = load(infile)
table = filter_RADEC(table,ramin,ramax,decmin,decmax)
table = filter_GalacticPlane(table)
table = filter_intpeak(table)
table = filter_region(table,mimtable)
save(table,outfile)

