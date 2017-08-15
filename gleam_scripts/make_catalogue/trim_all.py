#! python

"""
Input should be a joined table of priorized fitting.
Each column should have an affix of either _deep (for the white catalog) or _[freq] for the sub bands.
Output will be a table with a reduced number of columns.
sub band columns that are redundant are removed.
"""

__author__ = 'PaulHancock'

from astropy.table import Table
import numpy as np
import os, sys

if not len(sys.argv)==3:
    print "usage {0} input output".format(__file__)
    sys.exit(1)
input = sys.argv[-2]
output = sys.argv[-1]

freqs=[
"076",
"084",
"092",
"099",
"107",
"115",
"122",
"130",
"143",
"151",
"158",
"166",
"174",
"181",
"189",
"197",
"204",
"212",
"220",
"227"]


killring = ['peak_flux_deep','err_peak_flux_deep', 'flags_deep']
killring.extend( [ 'uuid_{0}'.format(f) for f in freqs])

cmd='stilts tcat in={0} out={1} icmd=\'delcols "{2}"\''.format(input,output,' '.join(killring))
print cmd
