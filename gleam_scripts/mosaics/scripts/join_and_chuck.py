#!/usr/bin/env python

# Extract only the best sources from the overlapping catalogues

import os
import sys
import glob
import shutil
import numpy as np
from astropy.io.votable import parse_single_table
from astropy.table import Table, Column
from astropy.io.votable import writeto as writetoVO

import re

prefix="Week"
suffix="_white_noweight_comp.vot"

table1=prefix+"1"+suffix
table2=prefix+"2"+suffix
table3=prefix+"3"+suffix
table4=prefix+"4"+suffix

# Crossmatch 1 with 2, 2 with 3, 3 with 4, 4 with 1, saving only things which overlap
if not os.path.exists('a1_2.vot'):
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table1+' in2='+table2+' out=a1_2.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=all join=1and2')
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table2+' in2='+table3+' out=a2_3.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=all join=1and2')
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table3+' in2='+table4+' out=a3_4.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=all join=1and2')
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table4+' in2='+table1+' out=a4_1.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=all join=1and2')
# Crossmatch 2 with 1, 3 with 2, 4 with 3, 1 with 4, saving only things which overlap
if not os.path.exists('a2_1.vot'):
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table2+' in2='+table1+' out=a2_1.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=all join=1and2')
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table3+' in2='+table2+' out=a3_2.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=all join=1and2')
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table4+' in2='+table3+' out=a4_3.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=all join=1and2')
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table1+' in2='+table4+' out=a1_4.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=all join=1and2')

# Grab each xmatch and select the values with the lowest RMSs (for now -- lowest resid_std might be best)
ands=["a1_2.vot","a2_3.vot","a3_4.vot","a4_1.vot"]
revands=["a2_1.vot","a3_2.vot","a4_3.vot","a1_4.vot"]

for amatch,rmatch in zip(ands,revands):
    output=amatch.replace(".vot","_best.vot")
    if not os.path.exists(output):
        print "Generating "+output
        a = parse_single_table(amatch)
        r = parse_single_table(rmatch)
        data_a = a.array
        data_r = r.array
        indices_a=np.where(data_a['local_rms_1']<data_a['local_rms_2'])
        indices_r=np.where(data_r['local_rms_1']<data_r['local_rms_2'])
        data_x = np.ma.concatenate([data_a[indices_a],data_r[indices_r]])
        vot = Table(data_x)
        writetoVO(vot, 'temp.vot')
    # Run through tpipe and keep the right columns (i.e. none of the _2 columns)
        os.system('stilts tpipe in=temp.vot cmd=\'keepcols "island source background local_rms ra_str dec_str ra err_ra dec err_dec peak_flux err_peak_flux int_flux err_int_flux a err_a b err_b pa err_pa flags residual_mean residual_std uuid"\' out='+output)
# For the older version of Aegean (no uuid)
        #os.system('stilts tpipe in=temp.vot cmd=\'keepcols "island source background local_rms ra_str dec_str ra err_ra dec err_dec peak_flux err_peak_flux int_flux err_int_flux a err_a b err_b pa err_pa flags residual_mean residual_std"\' out='+output)

# Not using XOR means we don't have to rename the columns later
# Crossmatch 1 with 2, 2 with 3, 3 with 4, 4 with 1, saving only things which DON'T overlap
if not os.path.exists('x1_2.vot'):
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table1+' in2='+table2+' out=x1_2.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=none join=1not2')
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table2+' in2='+table3+' out=x2_3.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=none join=1not2')
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table3+' in2='+table4+' out=x3_4.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=none join=1not2')
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table4+' in2='+table1+' out=x4_1.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=none join=1not2')
# Crossmatch 2 with 1, 3 with 2, 4 with 3, 1 with 4, saving only things which DON'T overlap
if not os.path.exists('x2_1.vot'):
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table1+' in2='+table2+' out=x2_1.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=none join=2not1')
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table2+' in2='+table3+' out=x3_2.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=none join=2not1')
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table3+' in2='+table4+' out=x4_3.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=none join=2not1')
    os.system('stilts tmatch2 matcher=skyellipse params=30 in1='+table4+' in2='+table1+' out=x1_4.vot values1="ra dec a b pa" values2="ra dec a b pa" ofmt=votable find=all fixcols=none join=2not1')

# Concatenate all of the tables together
os.system('stilts tcat in=x1_2.vot in=x2_3.vot in=x3_4.vot in=x4_1.vot in=x2_1.vot in=x3_2.vot in=x4_3.vot in=x1_4.vot in=a1_2_best.vot in=a2_3_best.vot in=a3_4_best.vot in=a4_1_best.vot out=complete.vot')
