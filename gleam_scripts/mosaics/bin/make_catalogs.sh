#! /bin/bash

# make the white catalogs

for w in 1 2 3 4 ; do
    echo "sed s/WEEK/Week${w}/g ~/templates/make_white_cat.tmpl > ~/queue/make_white_cat_week${w}.sh"
    echo "sbatch ~/queue/make_white_cat_week${w}.sh"
done

# make the narrow band psf maps and blind catalogs
# this is no longer required since Natasha makes these earlier in the processing stage.
#for w in 1 2 3 4 ; do
#   echo "sed s/WEEK/Week${w}/g ~/templates/make_psfs.tmpl > ~/queue/make_psfs_week${w}.sh"
#    echo "sbatch ~/queue/make_psfs_week${w}.sh"
#done

