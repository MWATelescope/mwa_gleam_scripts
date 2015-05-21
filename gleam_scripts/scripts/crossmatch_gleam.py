# !/bin/python
# Crossmatching script for total GLEAM and other SED samples (MS4 etc).

import os

print 'Crossmatching GLEAM'

if not os.path.exists(os.getcwd()+'/crossmatching'):
    os.makedirs(os.getcwd()+'/crossmatching')
    print 'Creating directory ', os.getcwd()+'/crossmatching'

os.system('stilts tmatchn matcher=skyellipse multimode=pairs nin=20 params=20 \
    in1=154-162MHz/Week2_154-162MHz.vot  values1="ra dec a b pa" \
    in2=072-080MHz/Week2_072-080MHz.vot  values2="ra dec a b pa" \
    in3=080-088MHz/Week2_080-088MHz.vot  values3="ra dec a b pa" \
    in4=088-095MHz/Week2_088-095MHz.vot  values4="ra dec a b pa" \
    in5=095-103MHz/Week2_095-103MHz.vot  values5="ra dec a b pa" \
    in6=103-111MHz/Week2_103-111MHz.vot  values6="ra dec a b pa" \
    in7=111-118MHz/Week2_111-118MHz.vot  values7="ra dec a b pa" \
    in8=118-126MHz/Week2_118-126MHz.vot  values8="ra dec a b pa" \
    in9=126-134MHz/Week2_126-134MHz.vot  values9="ra dec a b pa" \
    in10=139-147MHz/Week2_139-147MHz.vot values10="ra dec a b pa" \
    in11=147-154MHz/Week2_147-154MHz.vot values11="ra dec a b pa" \
    in12=162-170MHz/Week2_162-170MHz.vot values12="ra dec a b pa" \
    in13=170-177MHz/Week2_170-177MHz.vot values13="ra dec a b pa" \
    in14=177-185MHz/Week2_177-185MHz.vot values14="ra dec a b pa" \
    in15=185-193MHz/Week2_185-193MHz.vot values15="ra dec a b pa" \
    in16=193-200MHz/Week2_193-200MHz.vot values16="ra dec a b pa" \
    in17=200-208MHz/Week2_200-208MHz.vot values17="ra dec a b pa" \
    in18=208-216MHz/Week2_208-216MHz.vot values18="ra dec a b pa" \
    in19=216-223MHz/Week2_216-223MHz.vot values19="ra dec a b pa" \
    in20=223-231MHz/Week2_223-231MHz.vot values20="ra dec a b pa" \
    out=crossmatching/tot_mwa_154-162MHzbase.fits')

print 'Crossmatching GLEAM with MS4'

if not os.path.exists(os.getcwd()+'/crossmatching/ms4'):
    os.makedirs(os.getcwd()+'/crossmatching/ms4')
    print 'Creating directory ', os.getcwd()+'/crossmatching/ms4'

os.system('stilts tmatchn multimode=pairs nin=2 matcher=sky params=60 \
	in1=tot_mwa_154-162MHzbase.fits values1="ra_1 dec_1" \
	in2=MWA_Tools/catalogues/ms4.fits values2="RAJ2000 DEJ2000" \
	out=crossmatching/ms4/tot_mwa_154-162MHzbase+MS4.fits')

print 'Crossmatching GLEAM with ATCA database'

if not os.path.exists(os.getcwd()+'/crossmatching/atca_cali'):
    os.makedirs(os.getcwd()+'/crossmatching/atca_cali')
    print 'Creating directory ', os.getcwd()+'/crossmatching/atca_cali'

os.system('stilts tmatchn multimode=pairs nin=2 matcher=sky params=60 \
    in1=tot_mwa_154-162MHzbase.fits values1="ra_1 dec_1" \
    in2=MWA_Tools/catalogues/atcacaldb+mrc+sumss+vlssr+nvss.fits values2="RAJ2000 DEJ2000" \
    out=crossmatching/atca_cali/tot_mwa_154-162MHzbase+atcacaldb+mrc+sumss+vlssr+nvss.fits')

print 'Crossmatching GLEAM with Randall et al. (2011) sample'

if not os.path.exists(os.getcwd()+'/crossmatching/randall'):
    os.makedirs(os.getcwd()+'/crossmatching/randall')
    print 'Creating directory ', os.getcwd()+'/crossmatching/randall'

os.system('stilts tmatchn multimode=pairs nin=2 matcher=sky params=60 \
    in1=tot_mwa_154-162MHzbase.fits values1="ra_1 dec_1" \
    in2=MWA_Tools/catalogues/randall+mrc+sumss.fits values2="_RAJ2000 _DEJ2000" \
    out=crossmatching/randall/tot_mwa_154-162MHzbase+randall+mrc+sumss.fits')



