
# the my version of ~/templates is included in the ./templates directory

# Create a blank directory structure
for d in `cat d2copy.txt`
do
	mkdir ${d}
end

# Link files into the correct places
sbatch remake_dir.sh

# make catalogues from the white images without using the psfmaps
./make_white_nopsf.sh | bash

# make the psfmaps
# -> Natasha did this part, the result is a bunch of _rescaled.fits files
# -> These are symlinked in the `remake_dir.sh` script if they exist

# make catalogues from the white images WITH the psfmaps
# also includes QC filtering
./make_catalogs.sh | bash
# result: *_QC_comp.fits


# make priorised catalogues
./make_priorcats.sh | bash
# result: *_priorized_comp.fits

# combine all catalogues together
# rename columns
# create GLEAM source names
# add metadata
# remove sources in the zap.txt list
sbatch combine_all.sh
# result:
# - many temporary .fits files
# - GLEAMIDR6.fits
