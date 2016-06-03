from astropy.table.table import Table
from astropy.io.votable import from_table, writeto
import numpy as np
import sys

mids = """
076
084
092
099
107
115
122
130
143
151
158
166
174
181
189
197
204
212
220
227
""".split()

killring = ['Name', 'island_deep', 'source_deep', 'uuid_deep','flags_deep']
killring.extend([ 'uuid_{0}'.format(f) for f in mids])

print "table load"
tab = Table.read("all_wide.fits")
# remove columns we don't want
print "killing columns"
for n in killring:
    if n in tab.colnames:
        del tab[n]

print "renaming deep -> wide"
for n in tab.colnames:
    if 'deep' in n:
        tab[n].name = n.replace('deep','wide')

print "making names"
# make a new column which is the IAU source name
c = Table.Column(["GLEAM J"+(tab['ra_str_wide'][i][:-3]+tab['dec_str_wide'][i][:-3]).replace(':','') for i in range(len(tab))], name = 'Name')
tab.add_column(c,index=0)

print 'adding systematic error column'
# errs are 8% in most of the sky
errs = np.ones(len(tab))*8
# 13% above +18.5 
errs[np.where(tab['dec_wide']>=18.5)] = 13
# 13% below -72
errs[np.where(tab['dec_wide']<-72)] = 13
# 80% below -83.5
errs[np.where(tab['dec_wide']<-83.5)] = 80
c = Table.Column(errs, name='err_abs_flux_pct')
tab.add_column(c,index=21)

#rename some columns
print "renaming columns"

tab['dec_wide'].name = "DEJ2000"
tab['ra_wide'].name = "RAJ2000"
tab['err_ra_wide'].name = 'err_RAJ2000'
tab['err_dec_wide'].name = 'err_DEJ2000'
tab['ra_str_wide'].name = 'ra_str'
tab['dec_str_wide'].name = 'dec_str'

print "saving"
tab.write('GLEAMIDR4.fits')
