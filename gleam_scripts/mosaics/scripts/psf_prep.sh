#! /bin/bash

inputfile=${1}
sparse=${inputfile%%_comp.vot}_isolated_comp.vot
echo stilts tmatch1 matcher=sky values=\'ra dec\' params=600 action=keep0 in="${inputfile}" out="${sparse}"

    
psfvot=${inputfile%%_comp.vot}_prep_comp.vot
catdir=${MWA_CODE_BASE}/MWA_Tools/catalogues
MRCvot=${catdir}/MRC.vot
VLSSrvot=${catdir}/VLSSr.vot

# GLEAM: Get rid of crazy-bright sources, really super-extended sources, and sources with high residuals after fit
echo "stilts tpipe in=${sparse} cmd='select ((local_rms<1.0)&&((int_flux/peak_flux)<2)&&((residual_std/peak_flux)<0.1))' out=temp_crop.vot"

# MRC: get point like sources (MFLAG is blank)
Mmatchvot=${sparse%%_comp.vot}_MRC.vot
echo stilts tpipe in=${MRCvot} cmd=\'select NULL_MFLAG\' cmd=\'addcol PA_MRC \"0.0\"\' out=mrc_temp.vot

# Use only isolated sources
echo stilts tmatch1 matcher=sky values=\"_RAJ2000 _DEJ2000\" params=600 action=keep0 in=mrc_temp.vot out=mrc_crop.vot
    
# Match GLEAM with MRC
echo stilts tmatch2 matcher=skyellipse params=30 in1=mrc_crop.vot in2=temp_crop.vot out=temp_mrc_match.vot values1=\"_RAJ2000 _DEJ2000 2*e_RA2000 2*e_DE2000 PA_MRC\" values2=\"ra dec 2*a 2*b pa\" ofmt=votable

# Keep only basic aegean headings
echo stilts tpipe in=temp_mrc_match.vot cmd=\'keepcols \"ra dec peak_flux err_peak_flux int_flux err_int_flux local_rms a err_a b err_b pa err_pa residual_std flags\"\' out=${Mmatchvot}
    
# VLSSr: get point-like sources (a and b are < 86", same resolution as MRC); only sources North of Dec +20
Vmatchvot=${sparse%%_comp.vot}_VLSSr.vot

echo "stilts tpipe in=${VLSSrvot} cmd='select ((MajAx<.02389)&&(MinAx<0.02389)&&(_DEJ2000>0)) ' out=vlssr_temp.vot"

# Use only isolated sources
echo stilts tmatch1 matcher=sky values=\"_RAJ2000 _DEJ2000\" params=600 action=keep0 in=vlssr_temp.vot out=vlssr_crop.vot

# Match GLEAM with VLSSr
echo stilts tmatch2 matcher=sky params=120 in1=vlssr_crop.vot in2=temp_crop.vot out=temp_vlssr_match.vot values1=\"_RAJ2000 _DEJ2000\" values2=\"ra dec\" ofmt=votable


# Keep only basic aegean headings
echo stilts tpipe in=temp_vlssr_match.vot cmd=\'keepcols \"ra dec peak_flux err_peak_flux int_flux err_int_flux local_rms a err_a b err_b pa_2 err_pa residual_std flags\"\' out=${Vmatchvot}

# Concatenate the MRC and VLSSr matched tables together
echo stilts tcat in=${Mmatchvot} in=${Vmatchvot} out=${psfvot}
    
echo rm temp_crop.vot mrc_temp.vot mrc_crop.vot temp_mrc_match.vot vlssr_temp.vot vlssr_crop.vot temp_vlssr_match.vot ${Mmatchvot} ${Vmatchvot}
