#!/bin/bash -l

#SBATCH --account=mwasci
#SBATCH --partition=gpuq
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --mem=32gb
#SBATCH --output=/home/phancock/queue/combine_all.sh.o%A
#SBATCH --error=/home/phancock/queue/combine_all.sh.e%A

# debug output
set -x
java='aprun -d 1 -n 1 -b'
out="Week1-4_white_mosaic_psf_QC_comp.fits"
if [[ ! -e ${out} ]]
then
    echo "combining deep catalog from all weeks"
    $java stilts tcat \
	in=Week1/white/mosaic_Week1_170-231MHz_psf_QC_comp.fits \
	in=Week2/white/mosaic_Week2_170-231MHz_psf_QC_comp.fits \
	in=Week3/white/mosaic_Week3_170-231MHz_psf_QC_comp.fits \
	in=Week4/white/mosaic_Week4_170-231MHz_psf_QC_comp.fits \
	out=white_all.fits
    
    $java stilts tmatch1 matcher=sky params=60 action=keep0 values='ra dec' \
	in=white_all.fits out=white_singles.fits

    $java stilts tmatch1 matcher=sky params=60 action=wide2 values='ra dec' \
	in=white_all.fits out=white_dups.fits

    aprun -n 1 -d 1 python choose_source_double.py white_dups.fits white_dups_singles.fits

    $java stilts tcat \
	in=white_singles.fits \
	in=white_dups_singles.fits \
	out=${out}

    [[ $? ]] | exit
fi

# join all the frequencies together one week at a time
input=${out}
out="Week1-4_subs.fits"
if [[ ! -e ${out} ]]
then
    echo "making mutli frequency catalog from subs for each week"
    for week in Week1 Week2 Week3 Week4 
    do
	if [[ -e ${week}_subs.fits ]]; then continue;fi;
	$java stilts tmatchn multimode=pairs nin=20 matcher=exact \
	    in1=${week}/072-080MHz/mosaic_${week}_072-080MHz_priorized_comp.fits  values1='uuid'   suffix1='_076' \
	    in2=${week}/080-088MHz/mosaic_${week}_080-088MHz_priorized_comp.fits  values2='uuid'   suffix2='_084' \
	    in3=${week}/088-095MHz/mosaic_${week}_088-095MHz_priorized_comp.fits  values3='uuid'   suffix3='_092' \
	    in4=${week}/095-103MHz/mosaic_${week}_095-103MHz_priorized_comp.fits  values4='uuid'   suffix4='_099' \
	    in5=${week}/103-111MHz/mosaic_${week}_103-111MHz_priorized_comp.fits  values5='uuid'   suffix5='_107' \
	    in6=${week}/111-118MHz/mosaic_${week}_111-118MHz_priorized_comp.fits  values6='uuid'   suffix6='_115' \
	    in7=${week}/118-126MHz/mosaic_${week}_118-126MHz_priorized_comp.fits  values7='uuid'   suffix7='_122' \
	    in8=${week}/126-134MHz/mosaic_${week}_126-134MHz_priorized_comp.fits  values8='uuid'   suffix8='_130' \
	    in9=${week}/139-147MHz/mosaic_${week}_139-147MHz_priorized_comp.fits  values9='uuid'   suffix9='_143' \
	    in10=${week}/147-154MHz/mosaic_${week}_147-154MHz_priorized_comp.fits values10='uuid' suffix10='_151' \
	    in11=${week}/154-162MHz/mosaic_${week}_154-162MHz_priorized_comp.fits values11='uuid' suffix11='_158' \
	    in12=${week}/162-170MHz/mosaic_${week}_162-170MHz_priorized_comp.fits values12='uuid' suffix12='_166' \
	    in13=${week}/170-177MHz/mosaic_${week}_170-177MHz_priorized_comp.fits values13='uuid' suffix13='_174' \
	    in14=${week}/177-185MHz/mosaic_${week}_177-185MHz_priorized_comp.fits values14='uuid' suffix14='_181' \
	    in15=${week}/185-193MHz/mosaic_${week}_185-193MHz_priorized_comp.fits values15='uuid' suffix15='_189' \
	    in16=${week}/193-200MHz/mosaic_${week}_193-200MHz_priorized_comp.fits values16='uuid' suffix16='_197' \
	    in17=${week}/200-208MHz/mosaic_${week}_200-208MHz_priorized_comp.fits values17='uuid' suffix17='_204' \
	    in18=${week}/208-216MHz/mosaic_${week}_208-216MHz_priorized_comp.fits values18='uuid' suffix18='_212' \
	    in19=${week}/216-223MHz/mosaic_${week}_216-223MHz_priorized_comp.fits values19='uuid' suffix19='_220' \
	    in20=${week}/223-231MHz/mosaic_${week}_223-231MHz_priorized_comp.fits values20='uuid' suffix20='_227' \
	    out=${week}_subs.fits ofmt=fits-basic
    done

    [[ $? ]] | exit

# now concatenate all weeks together
    echo "concat all subs for all weeks"
    $java stilts tcat in=Week1_subs.fits in=Week2_subs.fits in=Week3_subs.fits in=Week4_subs.fits out=Week1-4_subs_long.fits

    echo 'relabeling/trimming catalog'
# relabel some of the columns and drop the ones that are not useful
    aprun -n 1 -d 1 python trim_subs.py Week1-4_subs_long.fits ${out} > temp.sh
    source temp.sh
    [[ $? ]] | exit
fi


# xmatch_white_subs.sh
final="GLEAMIDR6.fits"
if [[ ! -e ${final} ]]
then
    echo "combining deep and subs"
    # we use the new uuid column
    $java stilts tmatchn multimode=pairs nin=2 matcher=exact \
	in1=${input} values1='uuid' suffix1='_deep' join1=always \
	in2=${out} values2='uuid_final' suffix2='' \
	fixcols=all out=all_wide.fits ofmt=fits-basic
    [[ $? ]] | exit

fi

echo "Cleaning up catalog"
aprun -n 1 -d 1 python add_names.py all_wide.fits GLEAM_with_names.fits
aprun -n 1 -d 1 python update_meta.py GLEAM_with_names.fits GLEAM_with_meta.fits > update_meta.sh
source update_meta.sh
aprun -n 1 -d 1 python zap.py GLEAM_with_meta.fits ${final}
$java stilts tpipe in=${final} out=${final%%.fits}.vot ofmt='votable-binary-inline'
echo "done"
