#! /bin/bash

for w in 1 2 3 4 ; do
    echo "sed s/WEEK/Week${w}/g ~/templates/prior_fit.tmpl > ~/queue/prior_fit_week${w}.sh"
    echo "sbatch  ~/queue/prior_fit_week${w}.sh"
done
