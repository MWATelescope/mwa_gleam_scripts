/*  MWA C interface to CALCserv, for calculating u, v, w, delay
    Oct 2011. Natasha Hurley-Walker. Based on checkcalc.c in DiFX.

    This program interfaces to "CALC", which is distributed as an
    RPC server and calculates the u,v,w and delay for radio astronomy
    antennas using all sorts of corrections that are needed for VLBI.

    This code is primarily being used to check that precession corrections
    in corr2uvfits are being done correctly, but could later serve as an
    interface to CALC for uvfits files that are being generated on the fly.

    */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <ctype.h>
#include <fcntl.h>
#include <rpc/rpc.h>
#include <glob.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <assert.h>

#include "mwacalc.h"
#include "CALCServer.h"

#define MAX_ANT 128
#define ANT_NAME_LEN    16
#define DEFAULT_CALC_SERVER "curta.ivec.org"
#define DEFAULT_ANTFILE_NAME "antenna_proper_xyz.txt"

const char info[] = "$Id$";
const char progname[] = "mwacalc";

typedef struct {
    char *calcServer;
    char *antFileName;
    double RA;
    double Dec;
    double MJD;
} CommandLineOptions;

typedef struct {
    char name[ANT_NAME_LEN];
    double xyz[3];
} antenna;

static struct timeval TIMEOUT = { 10, 0 };

struct getCALC_res res;
static int debug = 0;
static FILE *fpd=NULL;      // file handle for debugging output

void usage()
{
    fprintf(stderr, "%s: Version info: %s\n\n", progname, info);
    fprintf(stderr, "A program to calculate u,v,w for MWA antenna positions using a calc server.\n\n");
    fprintf(stderr, "Usage : %s [options] { -r RA(J2000) -d Dec(J2000) -t MJD }\n\n", progname);
    fprintf(stderr, "options can include:\n");
    fprintf(stderr, "  --help\n");
    fprintf(stderr, "  -h       Print this help and quit\n");
    fprintf(stderr, "  -v       enable debugging output\n");
    fprintf(stderr, "  -s       <servername>   Use <servername> as calcserver\n");
    fprintf(stderr, "           By default %s will be the calcserver, but it needs to be on a local network.\n", DEFAULT_CALC_SERVER);
    fprintf(stderr, "  -a       <filename>   Load antenna file filename. Default: %s\n",DEFAULT_ANTFILE_NAME);
    fprintf(stderr, "\n");
    exit(0);
}


void processCmdLineOptions(int argc, char **argv, CommandLineOptions * opts) {
    int i;

    // print a usage message if no command-line args given
    if (argc < 2) usage();

    // set defaults
    opts->RA = -99.0;
    opts->Dec = -99.0;
    opts->MJD = -99.0;
    opts->antFileName = DEFAULT_ANTFILE_NAME;

    for (i = 1; i < argc; i++) {
    if (argv[i][0] == '-') {
        if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            usage();
        } else if (strcmp(argv[i], "-r") == 0 || strcmp(argv[i], "--RA") == 0) {
            i++;
            opts->RA = atof(argv[i]);
            if (debug) fprintf(fpd,"RA: %f\n", opts->RA);
        } else if (strcmp(argv[i], "-d") == 0 || strcmp(argv[i], "--Dec") == 0) {
            i++;
            opts->Dec = atof(argv[i]);
            if (debug) fprintf(fpd,"DEC: %f\n", opts->Dec);
        } else if (strcmp(argv[i], "-t") == 0 || strcmp(argv[i], "--MJD") == 0) {
            i++;
            opts->MJD = atof(argv[i]);
            if (debug) fprintf(fpd,"Time: %f\n", opts->MJD);
        } else if (strcmp(argv[i], "-a") == 0) {
            i++;
            // C uses indexing from zero
            opts->antFileName = argv[i];
        } else if (strcmp(argv[i], "-v") == 0 ) {
            // C uses indexing from zero
            debug=1;
        }
        else if (i + 1 < argc) {
            if (strcmp(argv[i], "--server") == 0 || strcmp(argv[i], "-s") == 0) {
                // skip to the next argument
                i++;
                opts->calcServer = argv[i];
            } else if (argv[i][0] == '-') {
                fprintf(stderr,"Error: Illegal option : %s\n", argv[i]);
                exit(0);
            }
        } else if (argv[i][0] == '-') {
            printf("Error: Illegal option : %s\n", argv[i]);
            exit(0);
        }
    }
    }
    /* sanity checks */
    if (opts->RA > (2.0*M_PI) || opts->RA < 0.0) {
        fprintf(stderr,"RA must be between 0 and 2pi radians (360deg)\n");
        exit(0);
    }
    if (fabs(opts->Dec) > (M_PI/2.0)) {
        fprintf(stderr,"Dec must be between -pi/2 and pi/2 radians (90deg)\n");
        exit(0);
    }
    if (opts->MJD < 0.0) {
        fprintf(stderr,"Must specify a valid MJD for time\n");
        exit(0);
    }

    if (opts->calcServer == NULL || strcmp(opts->calcServer, "") == 0) {
        opts->calcServer = DEFAULT_CALC_SERVER;
    }
    if (debug) fprintf(fpd,"CALC server: %s\n", opts->calcServer);
}


void deleteCalcParams(CalcParams * p) {
    free(p->calcServer);    // this was made via strdup() below
    free(p);
}

CalcParams *newCalcParams(const CommandLineOptions * opts) {
    CalcParams *p;

    p = (CalcParams *) calloc(1, sizeof(CalcParams));

    p->calcServer = strdup(opts->calcServer);
    p->calcProgram = CALCPROG;
    p->calcVersion = CALCVERS;

    // Create a connection with the calcserver
    p->clnt = clnt_create(p->calcServer, p->calcProgram, p->calcVersion, "tcp");

    if (!p->clnt) {
        clnt_pcreateerror(p->calcServer);
        printf("ERROR: rpc clnt_create fails for host : %-s\n", p->calcServer);
        deleteCalcParams(p);
        exit(1);
    }
    if (debug) fprintf(fpd,"RPC client created\n");

    return p;
}


/* load a file of antenna positions in absolute XYZ coords (VLBI coords). The file consists of 4
   columns with a name then X, Y, Z */
int getAntennas(const char *filename, antenna ants[MAX_ANT]) {
    FILE *file1;
    char buffer[100];
    int nant=0;

    // Loading in the antenna locations - generated from antenna_locations.txt via conv.py
    // python conv.py | grep proper_XYZ | awk '{printf "Tile%02d %s %s %s\n",NR, $2, $3, $4}' > antenna_proper_xyz.txt
    file1 = fopen(filename, "r");
    assert(file1 != NULL);
    nant = 0;
    while (fgets(buffer,100,file1) != NULL) {
        if (buffer[0]=='\n' || buffer[0]=='#') continue;    // skip blank/comment lines
        //if (debug) fprintf(fpd,"line: %s",buffer);
        sscanf(buffer,"%s %lf %lf %lf",ants[nant].name, &(ants[nant].xyz[0]),&(ants[nant].xyz[1]),&(ants[nant].xyz[2]));
        nant++;
    }

    fclose(file1);
    if (debug) fprintf(fpd,"nant=%d\n", nant);
    return (nant);
}


int CalcInit(CalcParams * p, const CommandLineOptions * opts, antenna ants[MAX_ANT], int ant) {
    struct getCALC_arg *request;
    int i;

    request = &(p->request);

    memset(request, 0, sizeof(struct getCALC_arg));

    request->request_id = 150;

    // set from command-line-options
    request->ra = opts->RA;
    request->dec = opts->Dec;
    request->date = opts->MJD;
    request->time = (opts->MJD) - (double) (request->date);

    // We don't know what kflags are
    for (i = 0; i < 64; i++) {
        request->kflags[i] = -1;
    }

    // proper motion params are zero
    request->dra = 0.0;
    request->ddec = 0.0;
    request->depoch = 0.0;
    request->parallax = 0.0;

    request->ref_frame = 0;
    request->pressure_a = 0.0;
    request->pressure_b = 0.0;

    request->source = "Test";

    request->station_a = "EC";  // this means "earth centre" and is treated specially by CALC.
    request->axis_type_a = "altz";
    request->axis_off_a = 0.0;

    request->station_b = "MWA";
    request->axis_type_b = "altz";
    request->axis_off_b = 0.0;

    //    printf("You asked for an obs at RA=%f, Dec=%f, MJD=%ld, SEC=%lf\n",request->ra,request->dec,(long)request->date,((double)request->time)*86400.0);

    // EOP parameters can be found at: http://gemini.gsfc.nasa.gov/solve_save/usno_finals.erp
    // they are typically of order less than an arcsec, so are unimportant for the MWA.
    // calc likes to have the EOPs for 2 days before and after the requested time so that it
    // can interpolate
    for (i = 0; i < 5; i++) {
        request->EOP_time[i] = opts->MJD + i - 2.0;
        request->tai_utc[i] = 35.0;         // TAI-UTC. Increases by 1 every leap second.
        request->ut1_utc[i] = 0.0;          // difference betwen ut1 and UTC, always < 1 sec.
        request->xpole[i] = 0.0;            // hard-code to zero for now.
        request->ypole[i] = 0.0;
    }

    request->a_x = 0.0;     // Earth centre
    request->a_y = 0.0;
    request->a_z = 0.0;

    request->b_x = ants[ant].xyz[0];
    request->b_y = ants[ant].xyz[1];
    request->b_z = ants[ant].xyz[2];

    return 0;
}


int run(const CommandLineOptions * opts) {
    CalcParams *p;
    antenna antpos[MAX_ANT];
    double uvw[MAX_ANT][3];
    int ant, nant, v;
    FILE *fout=stdout;
    enum clnt_stat clnt_stat;

    if (opts == 0) {
        return -1;
    }

    // this gets the parameters and opens the connection to the calc server        
    p = newCalcParams(opts);
    if (!p) {
        fprintf(stderr, "Cannot initialize CalcParams\n");
        return -1;
    }
    // This loads in the antenna file
    nant = getAntennas(opts->antFileName,antpos);
    if (debug) fprintf(fpd,"Loaded %d antennas\n",nant);

    // For each antenna, run the CalcServer
    for (ant = 0; ant < nant; ant++) {
        // Initialise parameters
        if (debug) fprintf(fpd,"Filling the 'request' array: antenna %s. (%g,%g,%g)\n", antpos[ant].name,
                            antpos[ant].xyz[0],antpos[ant].xyz[1],antpos[ant].xyz[2]);

        v = CalcInit(p, opts, antpos, ant);
        assert(v==0);

        memset(&res, 0, sizeof(struct getCALC_res));

        // Call the CalcServer
        // printf("Calling the calc server!\n");
        clnt_stat = clnt_call(p->clnt, GETCALC, (xdrproc_t) xdr_getCALC_arg,
              (caddr_t) & (p->request), (xdrproc_t) xdr_getCALC_res, (caddr_t) (&res), TIMEOUT);

        // Check if it worked
        if (clnt_stat != RPC_SUCCESS) {
            fprintf(stderr, "clnt_call failed!\n");
            fprintf(stderr, "clnt_stat was %d!\n", clnt_stat);
            clnt_perror(p->clnt, "client call");
            return -1;
        }
        if (res.error) {
            fprintf(stderr, "An error occured: %s\n", res.getCALC_res_u.errmsg);
//          abort();
            return -2;
        }
        memcpy(uvw[ant],res.getCALC_res_u.record.UV,sizeof(double)*3);
        // Print the results
        fprintf(fout, "Antenna %03d ('%s'): [%lf, %lf, %lf]\n", ant,antpos[ant].name,
                    res.getCALC_res_u.record.UV[0], res.getCALC_res_u.record.UV[1],
                    res.getCALC_res_u.record.UV[2]);

    }
    for (ant=1; ant<nant; ant++) {
        fprintf(fout,"Baseline 0-%d: [ %f,%f,%f ]\n",ant,uvw[0][0]-uvw[ant][0],uvw[0][1]-uvw[ant][1],uvw[0][2]-uvw[ant][2]);
    }
    deleteCalcParams(p);
    return 0;
}


int main(int argc, char **argv) {
    CommandLineOptions opts;

    fpd = stderr;   // set debugging out to stderr
    memset(&opts, 0, sizeof(CommandLineOptions));    // init to zero
    processCmdLineOptions(argc, argv, &opts);

    run(&opts);

    return 0;
}

