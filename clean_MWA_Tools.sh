#! /bin/bash
#cleans up the MWA_Tools builds 
#this is key to making sure systems specific things don't end up in the repo!

cd CONV2UVFITS; make clean
cd casatasks; make clean
cd build_lfiles; make clean
cd cfitsio; make clean
