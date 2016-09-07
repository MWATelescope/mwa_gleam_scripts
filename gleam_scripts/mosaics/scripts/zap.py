#! python

"""
Zap some sources that are in the GLEAM catalog, but which have been identified as false positivies via manual inspection.
"""

from astropy.io import fits
import numpy as np
import sys
__author__ = 'PaulHancock'


if not len(sys.argv)==3:
    print "usage zap.py input output"
    sys.exit(1)
input = sys.argv[-2]
output = sys.argv[-1]


def get_src_list():
    srcs = [s.strip() for s in open('sources_to_zap.txt').readlines()]
    print "found",srcs
    return srcs

def zap(table, names):
    """
    """
    print len(table["Name"])
    mask = np.where(np.bitwise_not(np.in1d(table['Name'],names)))
    print len(mask[0])
    return table[mask]


if __name__ == '__main__':
    names = get_src_list()
    table = fits.open(input)  # 'GLEAMIDR5.fits')
    ntable = zap(table[1].data,names)
    table[1].data = ntable
    table.writeto(output)  # "GLEAMIDR5_zapped.fits")
