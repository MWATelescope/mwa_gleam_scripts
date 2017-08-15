#! /usr/bin/env python

"""
Ingest a catalog of sources, which is the concatenation of multiple catalogs
Output a single catalog that has removed duplicate sources.
"""

import numpy as np
import os
import re
import sys
from astropy.table.table import Table


def get_colnames(table):
    """
    inspect to get a list of column names, without the _n affix
    """
    return [re.sub('_1$', '', a) for a in table.colnames if a[-2:] == '_1']


def count(row):
    """
    count the number of sources present in a row by counting the number of non-nan entries in ra column
    """
    col = 'ra'
    rmask = np.isfinite([row[col+'_1'],row[col+'_2'],row[col+'_3'],row[col+'_4']])
    nsrc = sum(rmask)
    return nsrc#, (np.array([1,2,3,4])[rmask]).tolist()


def strip_cols(table):
    # delete all the columns but the first and rename it to remove the affix _1
    for cname in colnames:
        table.rename_column(cname+'_1', cname)
    newtable = table[colnames]
    #del newtable['source'], newtable['island']
    return newtable


def shuffle_left_rows(tab, mask, idx):
    for c in colnames:
            tab[c+'_1'][mask] = tab[c+'_{0:d}'.format(idx)][mask]
    return tab


def main2():
    """
    As per main() but we operate on columns instead of rows. So much faster!
    """
    global colnames

    if len(sys.argv) !=3:
        print "Usage ", __file__, " inputcatalog outputcatalog"
        sys.exit()

    infile = sys.argv[-2]
    outfile = sys.argv[-1]

    print 'read'
    master = Table.read(infile)
    print 'colnames'
    colnames = get_colnames(master)
    print 'filtering'
    # don't have to worry about rows where the first col has the source we want
    second = np.where(master['local_rms_2'] <= master['local_rms_1'])
    master = shuffle_left_rows(master, second, 2)

    print "strip cols"
    master = strip_cols(master)
    print 'write'
    if os.path.exists(outfile):
        os.remove(outfile)
    master.write(outfile)


if __name__ == "__main__":
    main2()
