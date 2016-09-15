#! /usr/bin/env python

"""
update the metadata for the GLEAM IDR? source catalog.
"""
import sys
__author__ = "Paul Hancock"

if not len(sys.argv)==3:
    print "usage update_meta.py input output"
    sys.exit(1)
output = sys.argv[-1]
input = sys.argv[-2]

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


freqs = """072-080MHz
080-088MHz
088-095MHz
095-103MHz
103-111MHz
111-118MHz
118-126MHz
126-134MHz
139-147MHz
147-154MHz
154-162MHz
162-170MHz
170-177MHz
177-185MHz
185-193MHz
193-200MHz
200-208MHz
208-216MHz
216-223MHz
223-231MHz""".split()

metas = {}
metas['Name']              = {'ucd':'meta.id;src',                                     'units':''       ,'description':'IAU Name'}
metas['background_wide']   = {'ucd':'stat.median;phot.flux.density',                   'units':'Jy/beam','description':'Background level in wide image'}
metas['local_rms_wide']    = {'ucd':'stat.variance;phot.flux.density',                 'units':'Jy/beam','description':'Local noise leve in wide image'}
metas['ra_str']            = {'ucd':'pos.eq.ra;meta.main',                             'units':'h:m:s',  'description':'Right Ascension J2000'}
metas['dec_str']           = {'ucd':'pos.eq.dec;meta.main',                            'units':'d:m:s',  'description':"Declination J2000"}
metas['RAJ2000']           = {'ucd':'pos.eq.ra',                                       'units':'deg',    'description':'Right Ascension J2000'}
metas['DEJ2000']           = {'ucd':'pos.eq.dec',                                      'units':'deg',    'description':"Declination J2000"}
metas['err_RAJ2000']       = {'ucd':'stat.error;pos.eq.ra',                            'units':'deg',    'description':"Uncertainty in Right Ascension"}
metas['err_DEJ2000']       = {'ucd':'stat.error;pos.eq.dec',                           'units':'deg',    'description':"Uncertainty in Declination"}
metas['peak_flux_wide']    = {'ucd':'phot.flux.density;em.radio.170-231MHz',           'units':'Jy/beam','description':'Peak flux in wide image'}
metas['err_peak_flux_wide']= {'ucd':'stat.error;phot.flux.density;em.radio.170-231MHz','units':'Jy/beam','description':'Uncertainty in fit for peak flux in wide image'}
metas['int_flux_wide']     = {'ucd':'phot.flux;em.radio.170-231MHz',                   'units':'Jy',     'description':'Integrated flux in wide image'}
metas['err_int_flux_wide'] = {'ucd':'stat.error;phot.flux;em.radio.170-231MHz',        'units':'Jy',     'description':'Uncertainty in fit for integrated flux in wide image'}
metas['a_wide']            = {'ucd':'phys.angSize.smajAxis;meta.modelled',             'units':'arcsec', 'description':'Fitted semi-major axis in wide image'}
metas['err_a_wide']        = {'ucd':'stat.error;phys.angSize.smajAxis',                'units':'arcsec', 'description':'Uncertainty in fitted semi-major axis in wide image'}
metas['b_wide']            = {'ucd':'phys.angSize.sminAxis;meta.modelled',             'units':'arcsec', 'description':'Fitted semi-minor axis in wide image'}
metas['err_b_wide']        = {'ucd':'stat.error;phys.angSize.sminAxis',                'units':'arcsec', 'description':'Uncertainty in fitted semi-minor axis in wide image'}
metas['pa_wide']           = {'ucd':'pos.posAng;meta.modelled',                        'units':'deg',    'description':'Fitted position angle in wide image'}
metas['err_pa_wide']       = {'ucd':'stat.error;pos.posAng',                           'units':'deg',    'description':'Uncertainty in fitted position angle in wide image'}
metas['residual_mean_wide']= {'ucd':'stat.fit.residual',                               'units':'Jy/beam','description':'Mean value of data-model in wide image'}
metas['residual_std_wide'] = {'ucd':'stat.fit.residual',                               'units':'Jy/beam','description':'Standard deviation of data-model in wide image'}
metas['psf_a_wide']        = {'ucd':'phys.angSize.smajAxis;instr.det.psf',             'units':'arcsec', 'description':'Semi-major axis of the point spread function in wide image'}
metas['psf_b_wide']        = {'ucd':'phys.angSize.sminAxis;instr.det.psf',             'units':'arcsec', 'description':'Semi-minor axis of the point spread function in wide image'}
metas['psf_pa_wide']       = {'ucd':'pos.posAng;instr.det.psf',                        'units':'deg',    'description':'Position angle of the point spread function in wide image'}
metas['err_abs_flux_pct']  = {'ucd':'stat.error;phot.flux;em.radio',                   'units':'%',      'description':'Percent error in absolute flux scale - all frequencies'}

for mid,frange  in zip(mids,freqs):
    suffix = '_{0}'.format(mid)
    metas['background'+suffix]   = {'ucd':'stat.median;src;phot.flux.density',               'units':'Jy/beam','description':'Background level in '+frange+' image'}
    metas['local_rms'+suffix]    = {'ucd':'stat.variance;src;phot.flux.density',             'units':'Jy/beam','description':'Local noise level in '+frange+' image'}
    metas['peak_flux'+suffix]    = {'ucd':'phot.flux.density;em.radio.'+frange,              'units':'Jy/beam','description':'Peak flux in '+frange+' image'}
    metas['err_peak_flux'+suffix]= {'ucd':'stat.error;phot.flux.density;em.radio.'+frange,   'units':'Jy/beam','description':'Uncertainty in fit for peak flux in '+frange+' image'}
    metas['int_flux'+suffix]     = {'ucd':'phot.flux;em.radio.'+frange,                      'units':'Jy',     'description':'Integrated flux in '+frange+' image'}
    metas['err_int_flux'+suffix] = {'ucd':'stat.error;phot.flux;em.radio.'+frange,           'units':'Jy',     'description':'Uncertainty in fit for integrated flux in '+frange+' image'}
    metas['a'+suffix]            = {'ucd':'phys.angSize.smajAxis;src;meta.modelled',         'units':'arcsec', 'description':'Fitted semi-major axis in '+frange+' image'}
    metas['b'+suffix]            = {'ucd':'phys.angSize.sminAxis;src;meta.modelled',         'units':'arcsec', 'description':'Fitted semi-minor axis in '+frange+' image'}
    metas['pa'+suffix]           = {'ucd':'pos.posAng;meta.modelled',                        'units':'degree', 'description':'Fitted position angle in '+frange+' image' }
    metas['residual_mean'+suffix]= {'ucd':'stat.fit.residual',                               'units':'Jy/beam','description':'Mean value of data-model in '+frange+' image'}
    metas['residual_std'+suffix] = {'ucd':'stat.fit.residual',                               'units':'Jy/beam','description':'Standard deviation of data-model in '+frange+' image'}
    metas['psf_a'+suffix]        = {'ucd':'phys.angSize.smajAxis;instr.det.psf',             'units':'arcsec', 'description':'Semi-major axis of the point spread function in '+frange+' image'}
    metas['psf_b'+suffix]        = {'ucd':'phys.angSize.sminAxis;instr.det.psf',             'units':'arcsec', 'description':'Semi-minor axis of the point spread function in '+frange+' image'}
    metas['psf_pa'+suffix]       = {'ucd':'pos.posAng;instr.det.psf',                        'units':'deg',    'description':'Position angle of the point spread function in '+frange+' image'}

    
cmd = 'stilts tpipe in='+input+' out='+output+' ofmt="fits-plus" cmd="'
for k in metas.keys():
    cmd += "colmeta -units '{0[units]}' -ucd '{0[ucd]}' -desc '{0[description]}' '{1}'; ".format(metas[k],k)
cmd+='"'

print "aprun -n 1 -d 1 -b ", cmd
