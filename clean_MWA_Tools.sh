#! /bin/bash
#cleans up the MWA_Tools builds 
#this is key to making sure systems specific things don't end up in the repo!

cd CONV2UVFITS; make clean
cd ..
cd casatasks; make clean
cd ..
cd build_lfiles; make clean
cd ..
cd cfitsio; make clean
cd ..
