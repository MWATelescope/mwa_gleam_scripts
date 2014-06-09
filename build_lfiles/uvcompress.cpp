//
//  uvcompress.cpp
//  uvcompress - compression/decompression of MWA correlator dump files
//  using DEC compression schema
//
//  **Compression guideline (use only as indication, varies with data!)
//
//  Compression                     GZIP      RICE
//  Precision(decimal ponints)
//                      0           1:2.2     1:3.1
//                      1           1:2.1     1:2.3
//                      2           1:2.1     1:1.9
//                      3           1:1.9     1:1.6
//                      4           1:1.9     1:1.3
//
//  Created by Slava Kitaeff on 27/03/13.
//  Edited: 05/06/14
//  Copyright (c) 2013-14 ICRAR/UWA. All rights reserved.
//

#include "compress.h"

static void show_usage(string name)
{
    cerr << "Usage: " << name << " <option(s)> SOURCE DESTINATION\n"
    << "Options:\n"
    << "\t-h,--help\t\tShow this help message\n"
    << "\t-e, --expand\t\tExpand source FITS into destination FITS\n"
    << "\t-c, --compress\t\tCompress source FITS into destination FITS\n"
    << "\tRICE\t\t\tuse RICE compression (default if omited)\n"
    << "\tGZIP\t\t\tuse GZIP compression\n\n"
    << "\t-v\t\t\t\t\t\treport max difference and max relative difference\n"
    << "\t-d0, ... -d4\t\t\tforced precition as a number of decimal places (note no space) (-d0 is default if omited)\n"
    << "\t-d n        \t\t\tmultiply values by n before rounding and set BSCALE to n (note there is a space)\n"
    << "\t-h number_of_bins\t\toutput a histogram\n"
    << "\t-hh number_of_bins\t\toutput a histogram for each HDU\n\n"
    << "Note: Only image HDU containing 32-bit floating point data will be compressed.\n"
    << "\tAll other types of HDU will be copied over without modification.\n"
    << endl;
}

int main(int argc, const char * argv[])
{
    fitsfile *in;       // pointer to input FITS file
    fitsfile *out;      // pointer to output FITS file
    int status;         // returned status of FITS functions
    float bscale = 1;     // scale for forced precision
    int comp = RICE_1;  // compression type
    bool c = true;      // compress/decompress flag
    bool v = false;     // report the max difference
    int binnum = 0;         // number of bins for histogram
    int hbinnum = 0;         // number of bins for histogram for each HDU

    const char *InputFileName, *OutputFileName;
    
    if (argc < 3) { // We expect at least 3 arguments: the program name, the source path and the destination path
        show_usage(argv[0]);
        return 1;
    }
    
    // lets take the command line arguments
    string arg = argv[1];
    if ((arg == "-h") || (arg == "--help")) {
        show_usage(argv[0]);
        return 0;
    }
    
    for(int i=1; i<argc; ++i){
        arg = argv[i];
        if((arg == "-e") || (arg == "--expand"))   c = false; // expand
        if((arg == "-c") || (arg == "--compress"))   c = true; // compress
        if(c){
        if(arg == "RICE") comp = RICE_1;
        if(arg == "GZIP") comp = GZIP_1;
        if(arg == "-d0") bscale = 1;
        if(arg == "-d1") bscale = 10;
        if(arg == "-d2") bscale = 100;
        if(arg == "-d3") bscale = 1000;
        if(arg == "-d4") bscale = 10000;
        if(arg == "-d") sscanf(argv[i+1], "%f", &bscale);
        if(arg == "-v") v = true;
        if(arg == "-h") sscanf(argv[i+1], "%d", &binnum);
        if(arg == "-hh") sscanf(argv[i+1], "%d", &hbinnum);
        }
    }

    InputFileName = argv[argc-2];
    OutputFileName = argv[argc-1];
    
    //read FITS
    // Open specified file for read only access.
	fits_open_diskfile(&in, InputFileName, READONLY, &status);
 	PRINTERRMSG(status);
    
    //create new FITS file
    remove(OutputFileName);
    fits_create_file(&out, OutputFileName, &status);
  	PRINTERRMSG(status);

    time_t timerb, timere;
    time(&timerb);

    if(c)
        Compress(in, out, bscale, comp, v, binnum, hbinnum);
    else
        Decompress(in, out);

    time(&timere);
    cout << "Elapsed " << difftime(timere, timerb) << "sec.\n";
    
    fits_close_file(in, &status);
    PRINTERRMSG(status);
    fits_close_file(out, &status);
    PRINTERRMSG(status);
    
/*
    FILE *fd = fopen(OutputFileName, "wb");
    fwrite(memblock, sizeof(char), blockSize, fd);
    fclose(fd);
*/
    return 0;
}

