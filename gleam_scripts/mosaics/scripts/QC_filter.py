#!/usr/bin/env python

__author__ = "PaulHancock"

import os
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
    # hard coded ra/dec filter based on week.
    print "RADEC filter"
    if week==1:
        good = np.where((table['dec']<0) & ((table['ra']<=4*15 ) | (table['ra']>=20*15)))
        print good
    else:
        if week==2:
            ramin=0*15
            ramax=8*15
        elif week==3:
            ramin = 6*15
            ramax = 15*15
        elif week==4:
            ramin=14*15
            ramax=21*15
        else:
            print "bad week"
            sys.exit()
        good = np.where( (table['dec']<30) & (table['ra']>=ramin) & (table['ra']<=ramax))
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
        print 'MIMAS.py +c {0} {1} {2} -o {3}.mim'.format(v[0],v[1],v[2],k)
    everything = srclist.keys()
    print "MIMAS.py ",
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
    save(table, outfile)

