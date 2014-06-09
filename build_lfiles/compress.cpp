//
//  compress.cpp
//  uvcompress
//
//  Created by Slava Kitaeff on 2/04/13.
//  Edited: 09/06/14
//  Copyright (c) 2013-14 ICRAR/UWA. All rights reserved.
//

#include "compress.h"
#include <assert.h>


/* there is already a built-in round function in math.h type "man round"
#define round(r) (r>0.0)?floor(r+0.5):ceil(r-0.5)
*/

//
// fits_write_compressed()
//
// The function scales, decimates the data, and stores it in
// another FITS iamge file in compressed form.
//
// Arguments:
// *out - pointer to already opened destination FITS file
// *buff_in - pinter to the data array
// bscale - scaling factor used to force the precition
// comp - type of binary compression to use. Can be either RICE_1 or GZIP_1
// nelements - number of elements in array
// naxis & naxes[] - as per cfitsio library description
// maxabsdiff - maximum difference reported for the entire file
// maxreldiff - maximum relative difference reported for the entire file
// maxglobal - maximum for FITS file
// minglobal - mainmum for FITS file
// hbinnum - number of bins for HDU histogram
//
int fits_write_compressed(fitsfile *out,
                          float *buff_in,
                          LONGLONG nelements,
                          int naxis,
                          long *naxes,
                          float bscale,
                          int comp,
                          float maxabsdiff[],
                          float maxreldiff[],
                          float &maxglobal,
                          float &minglobal,
                          int hbinnum)
{
    int status = 0;    // returned status of FITS functions
    int *buff_out = (int*) malloc(sizeof(int) * nelements);
    float minbin = 0;
    float maxbin = 0;
    float tmp;
 
    if( buff_in == NULL){
        cerr << "Err: Could not allocate memory.";
        exit(EXIT_FAILURE);
    }

    for(int i=0; i<nelements; ++i){
        // round, decimate and convert
        buff_out[i] = (int)round(bscale * buff_in[i]);

        // find min, max
        minbin = buff_in[i] < minbin ? buff_in[i] : minbin;
        maxbin = buff_in[i] > maxbin ? buff_in[i] : maxbin;
        
        // calculate max diff and relative max diff
        tmp = fabs(buff_in[i] - buff_out[i] / bscale);
        if (tmp > maxabsdiff[1]){
            maxabsdiff[1] = tmp;
            maxabsdiff[0] = buff_in[i];
        }
        if (fabs(buff_in[i]) > 1e-1) {
            tmp = tmp / fabs(buff_in[i]);
            if (tmp > maxreldiff[1]){
                maxreldiff[1] = tmp;
                maxreldiff[0] = buff_in[i];
            }
        }
    }

    //build and output a histirgam for this HDU
    if( hbinnum )
    {
        int *hist = (int*) malloc(sizeof(int) * hbinnum);
        if( hist == NULL){
            cerr << "Err: Could not allocate memory.";
            exit(EXIT_FAILURE);
        }
        
        memset(hist, 0, sizeof(int) * hbinnum);

        float dr = (maxbin - minbin) / (hbinnum-1);
        
        // another pass to built the histogram
        int j;
        for(int i=0; i<nelements; ++i){
            j = (buff_in[i] - minbin)/dr;
            if(j >= hbinnum || j < 0) assert("Exceeds the index in histogram or negative");
            else
                hist[j]++;
        }
        
        //print the histogram data
        cout << "--------- Histogram ---------" << endl;
        cout << "First Bin = " << minbin << endl;
        cout << "Step = " << dr << endl;
        cout << "Number of bins = " << hbinnum << endl;
        for(int i=0; i<hbinnum; ++i)
                        cout << hist[i] << ";";
        cout << endl << endl;
        if( hist != NULL) free(hist);
    }
    
    //lets create HDU for encoded data
    fits_set_compression_type(out, comp, &status);
    PRINTERRMSG(status);
    
    fits_create_img(out, LONG_IMG, naxis, naxes, &status);
    PRINTERRMSG(status);
    
    fits_write_img(out, TINT, 1, nelements, buff_out, &status);
    PRINTERRMSG(status);

    // add the keys
    double bzero = 0;
    bscale = 1.0/bscale;
    fits_update_key(out, TFLOAT, "BSCALE", &bscale, NULL, &status);
    fits_update_key(out, TDOUBLE, "BZERO", &bzero, NULL, &status);
    PRINTERRMSG(status);
    
    // update global min, max
    minglobal = minbin < minglobal ? minbin : minglobal;
    maxglobal = maxbin > maxglobal ? maxbin : maxglobal;
    
    if(buff_out != NULL) free(buff_out);

    return 0;
}

//
// Compress()
//
// The function reads the source FITS image data, and stores it in
// another FITS iamge file in compressed form. The function works with
// 32-bit floating-point data only.
//
// Arguments:
// *in & *out - pointers to already opened source and destination FITS files correspondently
// bscale - scaling factor used to force the precition
// comp - type of binary compression to use. Can be either RICE_1 or GZIP_1
//
int Compress(fitsfile *in,
             fitsfile *out,
             double bscale,
             int comp,
             bool v,
             int binnum,
             int hbinnum)
{
    long naxes[]={1,1,1,1,1,1,1,1,1};
    int naxis=0;
    int status = 0;    // returned status of FITS functions
    int bitpix;
    LONGLONG nelements = 0;
    int count = 0;
    float maxabsdiff[] = {0.0, 0.0};
    float maxreldiff[] = {0.0, 0.0};
    float maxglobal = 0;
    float minglobal = 0;
    
    // loop through till the end of file
    while(status != END_OF_FILE){

        cout << "Reading HDU "<<count++ << endl;

        // get image dimensions and total number of pixels in image
        fits_get_img_param(in, 9, &bitpix, &naxis, naxes, &status);
        PRINTERRMSG(status);

        //copy and skip the first HDU, which has NAXIS=0
        if (naxis==0) {
            fits_copy_header(in, out, &status);
            PRINTERRMSG(status);
            cout << "HDU has NAXIS 0. Just copying header" << endl;
        }
        else {
            // read whole HDU and convert in one shot
            nelements = naxes[0] * naxes[1] * naxes[2] * naxes[3] * naxes[4] * naxes[5] * naxes[6] * naxes[7] * naxes[8];
        
            float *buff_in = (float*) malloc(sizeof(float) * nelements);
            if( buff_in == NULL ){
                cerr << "Err: Could not allocate memory.";
                exit(EXIT_FAILURE);
            }

            float nulval = 0.0;
            fits_read_img(in, TFLOAT, 1, nelements, &nulval, buff_in, NULL, &status);
            PRINTERRMSG(status);
        
            fits_write_compressed(out, buff_in, nelements, naxis, naxes, bscale, comp, maxabsdiff, maxreldiff, maxglobal, minglobal, hbinnum);

            if( buff_in != NULL ) free(buff_in);
        }
        // try next HDU
        fits_movrel_hdu(in, 1, NULL, &status);
    }

    // clear the error from trying to move past the last HDU from error stack
    status = 0;
    
    //build and output a histirgam for this FITS
    if( binnum )
    {
        int *hist = (int*) malloc(sizeof(int) * binnum);
        if( hist == NULL){
            cerr << "Err: Could not allocate memory.";
            exit(EXIT_FAILURE);
        }
        memset(hist, 0, sizeof(int) * binnum);

        //go back to the first HDU with data
        fits_movabs_hdu(in, 2, NULL, &status);
        PRINTERRMSG(status);
        
        // get image dimensions and total number of pixels in image
        fits_get_img_param(in, 9, &bitpix, &naxis, naxes, &status);
        PRINTERRMSG(status);
        
        nelements = naxes[0] * naxes[1] * naxes[2] * naxes[3] * naxes[4] * naxes[5] * naxes[6] * naxes[7] * naxes[8];
        
        float dr = (maxglobal - minglobal) / (binnum - 1);
     
        //go through the file again to build the histogram
        while(status != END_OF_FILE){
        
            float *buff_in = (float*) malloc(sizeof(float) * nelements);
            if( buff_in == NULL ){
                cerr << "Err: Could not allocate memory.";
                exit(EXIT_FAILURE);
            }
            
            float nulval = 0.0;
            fits_read_img(in, TFLOAT, 1, nelements, &nulval, buff_in, NULL, &status);
            PRINTERRMSG(status);
            
            // another pass to built the histogram
            int j;
            for(int i=0; i<nelements; ++i){
                j = (buff_in[i] - minglobal)/dr;
                if(j >= binnum || j < 0) assert("Exceeds the index in histogram or negative");
                    else
                        hist[j]++;
            }
            
            if( buff_in != NULL )free(buff_in);
            
            // try next HDU
            fits_movrel_hdu(in, 1, NULL, &status);
        }
        // clear the error from trying to move past the last HDU from error stack
        fits_clear_errmsg();

        cout.precision(12);
        
        //print the histogram data
        cout << endl << "================== File Statistics ==================" << endl;
        cout << "------ Histogram ------" << endl;
        cout << "First Bin = " << minglobal << endl;
        cout << "Step = " << dr << endl;
        cout << "Number of bins = " << binnum << endl;
        for(int i=0; i<binnum; ++i)
                    cout << hist[i] << ";";
        cout << endl;
        if(hist != NULL) free(hist);
    }

    if(v)
    {
        cout << endl;
        cout << "Largest abs diff: " << maxabsdiff[1] << " for the value " << maxabsdiff[0] << endl;
        cout << "Largest rel diff: " << maxreldiff[1] << " for the value " << maxreldiff[0] << endl;
        cout << endl;
    }
    
    return 0;
}


//
// Decompress()
//
// The function reads compressed source FITS image data, and stores it in
// another FITS iamge file in uncompressed form. The function works with
// DEC compressed data only.
//
// Arguments:
// *in & *out - pointers to already opened source and destination FITS files correspondently
//

int Decompress(fitsfile *in,
               fitsfile *out)
{
    int status = 0;    // returned status of FITS functions
    long naxes[]={1,1,1,1,1,1,1,1,1};
    int naxis;
    int bitpix;
    int hdutype;
    float nulval = 0.0;
    
    //loop through
    while(status != END_OF_FILE){

        //check if it's compressed image HDU
        fits_read_key(in, TLOGICAL, "ZIMAGE", &hdutype, NULL, &status);
        if( !hdutype ) {
            cerr << "Warrning: The data doesn't seem to be compressed. Nothing to be done.";
            return 1;
        }
        // get image dimensions and total number of pixels in image
        fits_get_img_param(in, 9, &bitpix, &naxis, naxes, &status);
        PRINTERRMSG(status);

        LONGLONG nelements = naxes[0] * naxes[1] * naxes[2] * naxes[3] * naxes[4] * naxes[5] * naxes[6] * naxes[7] * naxes[8];
        
        float *buff = (float*) malloc(sizeof(float) * nelements);
        if( buff == NULL ){
            cerr << "Err: Could not allocate memory!";
            exit(EXIT_FAILURE);
        }
        
        fits_read_img(in, TFLOAT, 1, nelements, &nulval, buff, NULL, &status);
        PRINTERRMSG(status);
        
        fits_create_img(out, FLOAT_IMG, naxis, naxes, &status);
        PRINTERRMSG(status);
        
        fits_write_img(out, TFLOAT, 1, nelements, buff, &status);
        PRINTERRMSG(status);
        
        if( buff != NULL ) free(buff);
        
        //move to the next HDU
        fits_movrel_hdu(in, 1, NULL, &status);
    }
    
    return 0;
}

