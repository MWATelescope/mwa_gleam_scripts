#!/bin/bash

# Cross-match the IDR catalogue with its spectral index version and make new columns

stilts tmatch2 matcher=exact join=all1 fixcols=dups in1=../GLEAMIDR6.fits in2=IDR6_alpha.vot values1=Name values2=Name out=GLEAMIDR6_alpha.fits suffix1="" suffix2="_del" \
    ocmd='addcol int_flux_fit_200 S_231*pow(200./231.,alpha)' \
    ocmd='addcol err_int_flux_fit_200 err_S_231*pow(200./231.,alpha)' \
    ocmd='addcol -after err_abs_flux_pct -ucd "stat.error;phot.flux;em.radio" -desc "Percent error on internal flux scale - all frequencies" -units "%" err_fit_flux_pct "DEJ2000 <= -72 || DEJ2000>= 18.5 ? toFloat(3) : toFloat(2)"' \
    ocmd='delcols "Name_del local_rms_wide_del RAJ2000_del DEJ2000_del peak_flux_wide_del int_flux_wide_del S_72 err_S_72 S_231 err_S_231"' \
    ocmd='replacecol -ucd "stat.fit;spect.index" -desc "Fitted spectral index" alpha "reduced_chi2 <= 1.93 ? toFloat(alpha) : NULL"'\
    ocmd='replacecol -ucd "stat.error;spect.index" -desc "Error on fitted spectral index" err_alpha "reduced_chi2 <= 1.93 ? toFloat(err_alpha) : NULL"' \
    ocmd='replacecol -ucd "stat.fit.chi2" -desc "Reduced chi^2 statistic for spectral index fit" reduced_chi2 "reduced_chi2 <= 1.93 ? toFloat(reduced_chi2 ): NULL"' \
    ocmd='replacecol -ucd "stat.fit;phot.flux;em.radio.200MHz" -desc "Fitted 200MHz integrated flux density" -units "Jy" int_flux_fit_200 "reduced_chi2 <= 1.93 ? toFloat(int_flux_fit_200) : NULL"' \
    ocmd='replacecol -ucd "stat.error;phot.flux;em.radio.200MHz" -desc "Error on fitted 200MHz integrated flux density" -units "Jy" err_int_flux_fit_200 "reduced_chi2 <= 1.93 ? toFloat(err_int_flux_fit_200) : NULL"' \
    ocmd='replacecol err_abs_flux_pct toFloat(err_abs_flux_pct)'

