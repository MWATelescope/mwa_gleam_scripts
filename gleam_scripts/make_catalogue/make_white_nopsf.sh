#! /bin/bash

# make the white catalogs

for w in 1 2 3 4 ; do
    echo "sed s/WEEK/Week${w}/g ~/templates/make_white_cat_npsf.tmpl > ~/queue/make_white_cat_npsf_week${w}.sh"
    echo "sbatch ~/queue/make_white_cat_npsf_week${w}.sh"
done
