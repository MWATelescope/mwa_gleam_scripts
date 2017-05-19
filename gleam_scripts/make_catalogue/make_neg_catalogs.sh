#! /bin/bash

# make the white catalogs

for w in 1 2 3 4 ; do
    echo "sed s/WEEK/Week${w}/g ~/templates/make_white_negs_cat.tmpl > ~/queue/make_white_negs_cat_week${w}.sh"
    echo "sbatch ~/queue/make_white_negs_cat_week${w}.sh"
done
