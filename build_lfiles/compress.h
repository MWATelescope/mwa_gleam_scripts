//
//  compress.h
//  uvcompress
//
//  Created by Slava Kitaeff on 2/04/13.
//  Copyright (c) 2013 ICRAR/UWA. All rights reserved.
//

#ifndef __uvcompress__compress__
#define __uvcompress__compress__

#include <iostream>
#include <string>
#include <math.h>
#include <time.h>
#include <stdio.h>
#include "fitsio.h"

using namespace std;

//#define DEC_KEY "DECIMATION"

#define PRINTERRMSG(status) {if (status != 0) { \
fits_report_error(stderr, status);              \
return status;                                  \
}}                                              \

// basic functions
int fits_write_compressed(fitsfile *out,
                          float *buff_in,
                          LONGLONG nelements,
                          int naxis,
                          long *naxes,
                          float bscale,
                          int comp,
                          float &maxabsdiff,
                          float &maxreldiff,
                          float &maxglobal,
                          float &minglobal,
                          int hbinnum);


int Compress(fitsfile *in,
             fitsfile *out,
             double bscale,
             int comp,
             bool v,
             int binnum,
             int hbinnum);
int Decompress(fitsfile *in, fitsfile *out);


#endif /* defined(__uvcompress__compress__) */
