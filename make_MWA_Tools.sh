#! /bin/bash
# a script for building all of the various MWA_Tools.. tools
# this should probably be a ./configure thingy but we just scientists and can't have nice things
#DJACOBS 
##
#To point to your own CFITSIO set the the CFITSIO environment variable to
#the root prefix of the library. eg
#if you have /usr/local/lib/libcfitsio.a
#then do 
#export CFITSIO=/usr/local/
# alternatively, most linux/Unix distros (including macports) set up the package
# manager so that pkg-config tells you both whether the package exists AND
# how to compile against it. Use a package manager unless you really,
# absolutely, have to install by hand.



echo "This is make_MWA_Tools.sh"

pkg-config --exists cfitsio
cfitsio_pkg_result=$?
if [ $cfitsio_pkg_result -ne 0 ] && [ -z $CFITSIO ]
then
  echo '$CFITSIO is not set, using internal CFITSIO'
  export CFITSLIB=../cfitsio/
  export CFITSINC=../cfitsio/
  cd cfitsio
  ./configure
  make
  if [ "$?" -ne 0 ];
      then
      echo 'internal cfitsio install failed'
      cd ..
      exit
  fi
  cd ..
else
    if [ -z "$CFITSLIB" ]
    then
        export CFITSLIB=${CFITSIO}/lib/
    else
        echo "CFITSLIB environment variable set to $CFITSLIB; overwriting default"
    fi
    if [ -z "$CFITSINC" ]
    then
        export CFITSINC=${CFITSIO}/include/
    else
        echo "CFITSINC environment variable set to $CFITSINC; overwriting default"
    fi
        echo 'using $CFITSIO = '${CFITSIO}
fi

echo "building LFILE & read_mwac utilities"
cd build_lfiles
make
if [ "$?" -ne 0 ];
    then
    echo "!!!!!!!!!!!!!!!!!!!!!!"
    echo 'build_lfiles/read_mwac make failed !'
    cd ..
    exit
fi
cd ..


echo "Building corr2uvfits"
cd CONV2UVFITS
make
if [ "$?" -ne 0 ];
    then
    echo "!!!!!!!!!!!!!!!!!!!!!!"
    echo 'CONV2UVFITS make failed'
    cd ..
    exit
fi




