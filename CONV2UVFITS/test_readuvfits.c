/*
*/

#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>
#include <assert.h>
#include "uvfits.h"

/* globals */
char *infilename=NULL;
int debug=0;
FILE *fpd;

void usage() {
    fprintf(stderr,"Usage:\n");
    fprintf(stderr,"test_readuvfits <options> -i inputfilename\n");
    fprintf(stderr,"\t-d debug_level (0=no debugging)\n");
    exit(0);
}


void parse_cmdline(const int argc,char * const argv[]) {
    int result=0;
    const char optstring[] = "d:i:";

    while ( (result = getopt(argc, argv, optstring)) != -1 ) {
        switch (result) {
          case 'i': infilename = optarg;
            break;
          case 'd': debug = atoi(optarg);
            break;
          default:
              fprintf(stderr,"unknown option: %c\n",result);
              usage(argv[0]);
        }
    }
}


int main(int argc, char *argv[]) {
    int res=0,chunk=0;
    uvdata *data_old,*data_new;
    uviterator *iter;

    fpd = stderr;
    if (argc < 2) usage();
    parse_cmdline(argc,argv);

    // set uvfits debugging output
    uvfitsSetDebugLevel(debug);

    if (debug) fprintf(fpd,"Reading file: %s\n",infilename);
    //res = readUVFITS(infilename,&data_old);
    if (res !=0) {
        fprintf(stderr,"readUVFITS failed with error %d\n",res);
    }

    /* now try the new way... */
/* */
    res = readUVFITSInitIterator(infilename, &data_new, &iter);
    if (res !=0) {
        fprintf(stderr,"readUVFITSInitIterator failed with error %d\n",res);
    }
    fflush(stdout);
    while ((res=readUVFITSnextIter(data_new,iter)) ==0) {
        fprintf(stdout,"Chunk %d. Time: %f. baselines: %d\n",chunk++,data_new->date[0],data_new->n_baselines[0]);
    }


    return 0;
}
