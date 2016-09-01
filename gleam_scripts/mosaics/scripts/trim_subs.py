#! python

"""
Input should be a joined table of priorized fitting.
Each column should have an affix of either _deep (for the white catalog) or _[freq] for the sub bands.
Output will be a table with a reduced number of columns.
sub band columns that are redundant are removed.
"""
import sys
__author__ = 'PaulHancock'


if not len(sys.argv)==3:
    print "usage trim_table.py input output"
    sys.exit(1)
input = sys.argv[-2]
output = sys.argv[-1]

# figure out which frequencies are included by looking at the uuid suffix
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

# keys that are to be ignored from the priorised catalogs
params = ['err_a','err_b','ra','ra_str','dec','dec_str','err_ra','err_dec',
          'err_pa','flags', 'source', 'island']#,'peak_flux','err_peak_flux']

killring = [ "{0}_{1}".format(p,f) for p in params for f in freqs]
cmd='aprun -n 1 -d 1 -b stilts tcat in={0} out={1} icmd=\'delcols "{2}"\''.format(input,output,' '.join(killring))
print cmd
