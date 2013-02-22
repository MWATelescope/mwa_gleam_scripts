/*
 * build_lfiles.c
 *
 *  Created on: Jul 20, 2012
 *      Author: sord
 */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <getopt.h>
#include <string.h>
#include <complex.h>
#include <unistd.h>
#include "mwac_utils.h"
#include "antenna_mapping.h"

#include "fitsio.h"

#define MAX_FILES   24


/* globals */
FILE *fpd;        //file hand for debug messages. Set this in main()
int npol;
int nstation;
int nfrequency;
int debug=0;

void printerror( int status)
{
    /*****************************************************/
    /* Print out cfitsio error messages and exit program */
    /*****************************************************/

    char status_str[FLEN_STATUS], errmsg[FLEN_ERRMSG];

    if (status)
        fprintf(stderr, "\n*** Error occurred during program execution ***\n");

    fits_get_errstatus(status, status_str);   /* get the error description */
    fprintf(stderr, "\nstatus = %d: %s\n", status, status_str);

    /* get first message; null if stack is empty */
    if ( fits_read_errmsg(errmsg) )
    {
        fprintf(stderr, "\nError message stack:\n");
        fprintf(stderr, " %s\n", errmsg);

        while ( fits_read_errmsg(errmsg) )  /* get remaining messages */
            fprintf(stderr, " %s\n", errmsg);
    }

    exit( status );       /* terminate the program, returning error status */
}

void usage() {

    fprintf(stdout,"build_lfiles:\n");
    fprintf(stdout,"create lfiles (autos and X) from a correlator dump (mode 0) or an NGAS FITS file (mode 1)\n");
    fprintf(stdout,"Options:\n");
    fprintf(stdout,"\t-m\t 0|1|2 [default == 0]: read a raw correlator dump\n\t\t 1: read an NGAS FITS FILE\n\t\t 2: Read an OLD format raw correlator dump\n");
    fprintf(stdout,"\t-v\t <visibility file name> -- this argument can appear multiple times. Each file is concatenated in frequency <NOT TIME>\n");
    fprintf(stdout,"\t-f\t <nfrequency> [default == 1536]: Number of channels <must equal nfiles*nchan_per_file>\n");
    fprintf(stdout,"\t-i\t <number of inputs> [default == 64] : number of input that have been correlated <nstation*npol>\n");
    fprintf(stdout,"\t-o\t <output filename root> [default == \"last_dump\"] root filename of the output\n");
    fprintf(stdout,"\t-s\t <start> -- seconds from beginning of file to start. Default: 0\n");
    fprintf(stdout,"\t-n\t <nseconds> -- how many seconds to process. Default: all\n");
    fprintf(stdout,"\t-T\t <factor> [default == 1] -- by what factor to average in time\n");
    fprintf(stdout,"\t-F\t <factor> [default == 1] -- by what factor to average in frequency\n");
    fprintf(stdout,"\t-p\t -- image in primary header -- NOW ASSUMED IF MODE == 0\n");
    fprintf(stdout,"\t-a\t append to output instead of clobber\n");
    fprintf(stdout,"\t-d\t enable debugging messages\n");

    exit(EXIT_FAILURE);
}


void getNumHDUsInFiles(int nfiles, char *infilename[MAX_FILES], int num_hdus_in_file[MAX_FILES], int file_type[MAX_FILES]) {
    fitsfile *fptr;
    int status=0,i;

    for (i=0; i< nfiles; i++) {
        if (!fits_open_file(&fptr, infilename[i], READONLY, &status)) {
            if (fits_get_num_hdus(fptr,num_hdus_in_file+i,&status)) {
                printerror(status);
            }
            if (debug) fprintf(fpd,"There are %d HDUs in file %s\n",num_hdus_in_file[i],infilename[i]);
            /* move to the last one and see what it is */
            if (fits_movabs_hdu(fptr, num_hdus_in_file[i], file_type+i, &status)){
                fprintf(stderr,"Error moving to HDU %d\n",num_hdus_in_file[i]);
                printerror(status);
            }
            if (debug) fprintf(fpd,"The last HDU is type %d\n",file_type[i]);
            fits_close_file(fptr,&status);
        }
        else {
            fprintf(stderr,"Cannot open file %s\n",infilename[i]);
            exit(1);
        }
    }

	/* sanity checks */
	for (i=1; i< nfiles; i++) {
		if ( abs(num_hdus_in_file[i]-num_hdus_in_file[i-1]) > 1) {
			fprintf(stderr,"ERROR: serious mismatch between number of HDUs in files (%d vs %d). Exiting.\n",
							num_hdus_in_file[i],num_hdus_in_file[i-1]);
			exit(EXIT_FAILURE);
		}
	}
}

int main(int argc, char **argv) {

    int arg = 0;
    int mode = 0; // mode 0 is single timestep from a correlator dump
    // mode 1 is multiple timesteps from a FITS file

    char *input_file[MAX_FILES];
    char *output_file = NULL;
    int num_hdus_in_file[MAX_FILES];
    int last_hdu_type[MAX_FILES];
    int ninput = 64;
    int nfiles = 0;
    int start_sec = 0;
    int nseconds = 99999;
    int fscrunch_factor=1;
    int tscrunch_factor=1;
    int primary = 1; //image NOT in primary header?: see NGAS (1==true)
    extern int nfrequency;
    extern char *optarg;

    extern int npol;
    extern int nstation;

    fpd = stdout;

    nstation = 32;
    nfrequency = 1536;
    npol = 2;
    ninput = nstation*npol;

    // should we append or overwrite the output file
    int appendtofile=0;
    char lccfilename[1024];        
    char lacfilename[1024];

    char tmp_lccfilename[1024];        
    char tmp_lacfilename[1024];


    if (argc == 1) {
        usage();
    }

    memset(num_hdus_in_file,0,sizeof(num_hdus_in_file));

    while ((arg = getopt(argc, argv, "m:i:f:F:s:v:n:o:apT:d")) != -1) {

        switch (arg) {
            case 'h':
                usage();
                break;
            case 'v':
                input_file[nfiles] = strdup(optarg);
                nfiles++;
                break;
            case 'm':
                mode = atoi(optarg);
                break;
            case 'i':
                ninput = atoi(optarg);
                nstation = ninput/npol;
                break;
            case 'f':
                nfrequency = atoi(optarg);
                break;
            case 'F':
                fscrunch_factor = atoi(optarg);
                break;
            case 's':
                start_sec = atoi(optarg);
                break;
            case 'n':
                nseconds = atoi(optarg);
                break;
            case 'o':
                output_file = strdup(optarg);
                break;
            case 'p':
                primary = 0;
                break;
            case 'a':
                appendtofile = 1;
                break;
            case 'T':
                tscrunch_factor = atoi(optarg);
                break;
            case 'd':
                debug++;
                break;
            default:
                usage();
                break;
        }


    }

    if (nfiles == 0) {
        mode = 0;
        input_file[0] = "/tmp/last_dump.fits";
        nfiles = 1;

    }
    if (output_file == NULL) {
        output_file = "last_dump";
    }
    float complex *cuda_matrix_h = NULL;
    float complex *full_matrix_h = NULL;
    float complex null = 0x0;
    float complex * lccspc_h = NULL; 
    float complex * lcc_base = NULL;
    float * lacspc_h = NULL; 
    float * lac_base = NULL ;

    size_t nvis = (nstation + 1)*(nstation/2)*npol*npol;

    size_t matLength = nfrequency * nvis; // cuda_matrix length (autos on the diagonal)
    size_t lccspcLength = nfrequency * (ninput-1)*ninput/2; //Lfile matrix length (no autos)
    size_t lacspcLength = nfrequency * ninput; //Lfile autos length
    size_t fullLength = nfrequency * ninput*ninput;

    int ifile;
    int ihdu = 1+start_sec;
    int stophdu;

    cuda_matrix_h = (float complex *) malloc(matLength * sizeof(float complex));
    full_matrix_h = (float complex *) malloc(fullLength * sizeof(float complex));
    lccspc_h = (float complex *) malloc(lccspcLength*sizeof(float complex));
    lacspc_h = (float *) malloc(lacspcLength*sizeof(float));

    lcc_base = lccspc_h;
    lac_base = lacspc_h;

    if (mode == 0)
        primary = 0;
    ihdu += primary;    // the data starts in header ihdu.
    stophdu = ihdu + nseconds-1;
    /* find out how many HDUs are in each file */
    getNumHDUsInFiles(nfiles,input_file,num_hdus_in_file,last_hdu_type);

    /* check that there are the same number of HDUs in each file and only extract the amount of time
        that there is actually data for */
    for (ifile=0; ifile < nfiles; ifile++) {
        if (stophdu > num_hdus_in_file[ifile]) {
            stophdu = num_hdus_in_file[ifile];
        }
    }

    if (mode == 1 || mode == 0) {
        /* new format vis file: vis are in image, not binary table */
        fitsfile *fptr;      /* FITS file pointer, defined in fitsio.h */
        int status = 0;   /*  CFITSIO status value MUST be initialized to zero!  */
        int hdutype, ncols, typecode;
        long nrows,repeat,width_in_bytes;

        if (debug) fprintf(fpd,"Start HDU: %d, stop HDU: %d\n",ihdu,stophdu);

        sprintf(lccfilename,"%s.LCCSPC",output_file);
        sprintf(lacfilename,"%s.LACSPC",output_file);

        sprintf(tmp_lccfilename,"%s.working.LCCSPC",output_file);
        sprintf(tmp_lacfilename,"%s.working.LACSPC",output_file);


        FILE *autos=NULL;
        FILE *cross=NULL;

        // if averaging later, then write to a temp file
        // otherwise write directly to output file
            if (tscrunch_factor != 1 || fscrunch_factor != 1) {
                autos = fopen(tmp_lacfilename,"w");
                cross = fopen(tmp_lccfilename,"w");
        }
        else {
	  if (!appendtofile) {
	    autos = fopen(lacfilename,"w");
	    cross = fopen(lccfilename,"w");
	  }
	  else {
	    autos = fopen(lacfilename,"a");
	    cross = fopen(lccfilename,"a");
	  }
        }

        if (autos == NULL || cross == NULL) {
            fprintf(stderr,"Cannot open %s or %s\n",lacfilename,lccfilename);
            exit(EXIT_FAILURE);
        }

        fill_mapping_matrix();

        while (ihdu <= stophdu) {

            for (ifile = 0; ifile < nfiles; ifile++) {
                if (debug) fprintf(fpd,"Opening file %s for time step %d\n",input_file[ifile],ihdu);

                if (!fits_open_file(&fptr, input_file[ifile], READONLY, &status))
                {
                    status=0;

                    /* Get the HDU type */
                    if (last_hdu_type[ifile] == BINARY_TBL) {

                        if (debug) fprintf(fpd,"Detected Binary Table HDU\n");

                        fits_movabs_hdu(fptr, ihdu, &hdutype, &status);
                        if (status != 0) {
                                printf("Error - advance past last HDU");
                                status = 0;
                                fits_close_file(fptr,&status);
                                goto SHUTDOWN;
                        }

                        fits_get_num_rows(fptr, &nrows, &status);
                        fits_get_num_cols(fptr, &ncols, &status);

                        status = 0;
                        fits_get_coltype(fptr,1,&typecode,&repeat,&width_in_bytes,&status);
                        if (debug) {
                            fprintf(fpd,"table have %ld rows and %d cols\n",nrows,ncols);
                            fprintf(fpd,"each col is type %d with %ld entries and %ld bytes long\n",typecode,repeat,width_in_bytes);
                        }

                        if (nfrequency != (nrows*nfiles)) {
                            fprintf(stderr, "nfiles (%d) * nrows (%ld) not equal to nfrequency (%d) are the FITS files the dimension you expected them to be?\n",\
                                    nfiles,nrows,nfrequency);
                            exit(EXIT_FAILURE);
                        }

                        int anynull = 0x0;

                        float complex *ptr = cuda_matrix_h + (ifile * nrows * nvis);

                        status = 0;
                        fits_read_col(fptr,typecode,1,1,1,(repeat*nrows),&null,ptr,&anynull,&status);
                        if (status != 0 ) {
                            printf("Error reading columns");
                        }
                    }
                    else {
                        if (debug) fprintf(fpd,"Not binary table: assuming image extension\n");

                        if (fits_movabs_hdu(fptr, ihdu, &hdutype, &status)){
                            printerror(status);
                        }

                        status=0;
                        long fpixel = 1;
                        float nullval = 0;
                        int anynull = 0x0;
                        int nfound = 0;
                        long naxes[2];
                        long npixels = 0;

                        if (fits_read_keys_lng(fptr,"NAXIS",1,2,naxes,&nfound,&status)) {
                            printerror(status);
                        }

                        status = 0;
                        npixels = naxes[0] * naxes[1];

                        if (nfrequency != (naxes[1]*nfiles)) {
                            fprintf(stderr, "nfiles (%d) * nrows (%ld) not equal to nfrequency (%d) are the FITS files the dimension you expected them to be?\n",\
                                    nfiles,naxes[1],nfrequency);
                            exit(EXIT_FAILURE);
                        }


                        float complex *ptr = cuda_matrix_h + (ifile * naxes[1] * nvis);
                        if (fits_read_img(fptr,TFLOAT,fpixel,npixels,&nullval,(float *)ptr,&anynull,&status)) {
                            printerror(status);
                        }
                        //
                        // now need to read in the relevant part of the image
                        //
                        //

                    }
                }
                else {
                    printf("Error failed to open %s\n",input_file[ifile]);
                    exit(EXIT_FAILURE);
                }
                status = 0;
                fits_close_file(fptr,&status);
            }

            printf("Extracting matrix\n");        
            extractMatrix(full_matrix_h, cuda_matrix_h);
            /* now build lfile data */        
            int input1=0,input2=0;
            for (input1 = 0; input1 < ninput; input1++) {
                for (input2 = input1 ; input2 < ninput; input2++) {
                    map_t the_mapping = corr_mapping[input1][input2];
                    get_baseline_lu(the_mapping.stn1, the_mapping.stn2, the_mapping.pol1,
                            the_mapping.pol2, full_matrix_h, lccspc_h);
                    if (input1 == input2) {
                        /* auto */
                        int i=0;
                        for (i=0;i<nfrequency;i++) {
                            *lacspc_h = crealf(lccspc_h[i]);
                            lacspc_h++;
                        }

                    }
                    else {
                        /* cross */
                        lccspc_h += nfrequency;
                    }
                }

            }


            fwrite(lac_base,sizeof(float),lacspcLength,autos);
            fwrite(lcc_base,sizeof(float complex),lccspcLength,cross);
            lacspc_h = lac_base;
            lccspc_h = lcc_base;

            ihdu++;
        }
SHUTDOWN:
        fclose(autos);
        fclose(cross);

    }
    else if (mode == 2) {
        /* old format vis file */
        FILE *matrix;
        int rtn;
        float complex *cuda_matrix_h = NULL;
        float complex *full_matrix_h = NULL;

        float complex * lccspc_h = NULL; 
        float complex * lcc_base = NULL;
        float * lacspc_h = NULL; 
        float * lac_base = NULL ;

        size_t matLength = nfrequency * (ninput+npol)*ninput/2; // cuda_matrix length (autos on the diagonal)
        size_t lccspcLength = nfrequency * (ninput-1)*ninput/2; //Lfile matrix length (no autos)
        size_t lacspcLength = nfrequency * ninput; //Lfile autos length
        size_t fullLength = nfrequency *ninput*ninput;

        cuda_matrix_h = (float complex *) malloc(matLength * sizeof(float complex));
        full_matrix_h = (float complex *) malloc(fullLength * sizeof(float complex));
        lccspc_h = (float complex *) malloc(lccspcLength*sizeof(float complex));
        lacspc_h = (float *) malloc(lacspcLength*sizeof(float));

        lcc_base = lccspc_h;
        lac_base = lacspc_h;

        matrix = fopen(input_file[0], "r");

        if (matrix == NULL) {
            perror("On opening file");
            exit(EXIT_FAILURE);
        }

        rtn = fread(cuda_matrix_h, sizeof(float complex), matLength, matrix);

        if (rtn != matLength) {
            if (!feof(matrix)) {
                perror("On reading file");
            } else {

                fprintf(stderr,
                        "EOF before full matrix read (partial read of %d elemetns)\n",
                        rtn);
                exit(EXIT_FAILURE);
            }
        } else {


            fprintf(stdout,
                    "Full matrix read in for a single time step  -- will reorder to triangular\n");
            // wacky packed tile order to packed triangular
            // xgpuReorderMatrix((Complex *) cuda_matrix_h);
            // convert from packed triangular to full matrix
            extractMatrix_slow(full_matrix_h, cuda_matrix_h);
            // get the mapping
            fill_mapping_matrix();
        }

        /* now build lfile data */
        int input1=0,input2=0;
        for (input1 = 0; input1 < ninput; input1++) {
            for (input2 = input1 ; input2 < ninput; input2++) {
                map_t the_mapping = corr_mapping[input1][input2];
                get_baseline_lu(the_mapping.stn1, the_mapping.stn2, the_mapping.pol1,
                        the_mapping.pol2, full_matrix_h, lccspc_h);
                if (input1 == input2) {
                    /* auto */
                    int i=0;
                    for (i=0;i<nfrequency;i++) {
                        *lacspc_h = crealf(lccspc_h[i]);
                        lacspc_h++;
                    }

                }
                else {
                    /* cross */
                    lccspc_h += nfrequency;
                }
            }

        }
        FILE *autos=NULL;
        FILE *cross=NULL;
        autos = fopen("last_dump.LACSPC","w");
        fwrite(lac_base,sizeof(float),lacspcLength,autos);
        fclose(autos);
        cross = fopen ("last_dump.LCCSPC","w");
        fwrite(lcc_base,sizeof(float complex),lccspcLength,cross);
        fclose(cross);

        fclose(matrix);
        exit(EXIT_SUCCESS);

    }

    if (tscrunch_factor != 1 || fscrunch_factor != 1) {

        fprintf(stdout,"Averaging %d time samples\n",tscrunch_factor);
        fprintf(stdout,"Averaging %d frequency samples\n",fscrunch_factor);

        FILE *tmp_autos = NULL;
        FILE *tmp_cross = NULL;
        FILE *autos=NULL;
        FILE *cross=NULL;
        
               tmp_autos = fopen(tmp_lacfilename,"r");
        tmp_cross = fopen(tmp_lccfilename,"r");
        autos = fopen(lacfilename,"w");
        cross = fopen(lccfilename,"w");


        float complex * lccspc_tmp;
        float * lacspc_tmp;

        lccspc_tmp = (float complex *) malloc(lccspcLength*sizeof(float complex)/fscrunch_factor);
        lacspc_tmp = (float *) malloc(lacspcLength*sizeof(float)/fscrunch_factor);

        int i=0,j=0,t=0;
        size_t rtn = 0;

        while (!feof(tmp_autos) ) {

            bzero(lacspc_tmp,lacspcLength*sizeof(float)/fscrunch_factor);
            for (t=0;t<=tscrunch_factor;t++) {
                rtn = fread(lac_base,sizeof(float),lacspcLength,tmp_autos);
                if (rtn == lacspcLength) {
                    float *lac_ptr = lac_base;
                    for (i=0;i<(lacspcLength/fscrunch_factor);i++) {
                        for (j=0;j<fscrunch_factor;j++) {
                            lacspc_tmp[i] += *lac_ptr;
                            lac_ptr++;
                        }
                    }

                }
                else {
                    break; // out of this for loop - t == normalisation factor
                }
            }
            if (t != 0) {        
                for (i=0;i<lacspcLength/fscrunch_factor;i++) {
                    lacspc_tmp[i] /= (t*fscrunch_factor);
                }
                fwrite(lacspc_tmp,sizeof(float),lacspcLength/fscrunch_factor,autos);
            }
        }

        fclose(autos);
        fclose(tmp_autos);

        while (!feof(tmp_cross) ) {

            bzero(lccspc_tmp,lccspcLength*sizeof(float complex)/fscrunch_factor);
            for (t=0;t<=tscrunch_factor;t++) {
                rtn = fread(lcc_base,sizeof(float complex),lccspcLength,tmp_cross);
                if (rtn == lccspcLength) {
                    float complex *lcc_ptr = lcc_base;
                    for (i=0;i<lccspcLength/fscrunch_factor;i++) {
                        for (j=0;j<fscrunch_factor;j++) {
                            lccspc_tmp[i] += *lcc_ptr;
                            lcc_ptr++;
                        }
                    }
                }
                else {
                    break; // out of this for loop - t == normalisation factor
                }
            }
            if (t != 0) {        
                for (i=0;i<lccspcLength/fscrunch_factor;i++) {
                    lccspc_tmp[i] /= (t*fscrunch_factor);
                }
                fwrite(lccspc_tmp,sizeof(float),lacspcLength/fscrunch_factor,cross);
            }
        }

        fclose(cross);
        fclose(tmp_cross);

        free(lccspc_tmp);
        free(lacspc_tmp);

    }

    free(lcc_base);
    free(lac_base);

    return 0;
}
