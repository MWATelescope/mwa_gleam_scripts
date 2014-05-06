/* Program to apply geometric and cable length corrections to
 * "L-file" data. Based heavily on corr2uvfits which has had
 * the core code pulled out into convutils.
 *  Randall Wayth. May 2014.
*/

#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <complex.h>
#include <math.h>
#include <ctype.h>
#include <assert.h>
#include "slalib.h"
#include "uvfits.h"
#include "convutils.h"

typedef struct {
    char *outccfilename;
    char *outacfilename;
    char *stationfilename;
    char *configfilename;
    char *header_filename;
    char *crosscor_filename;
    char *autocorr_filename;
    char *flagfilename;
    double arr_lat_rad;
    double arr_lon_rad;
    double height;
    int do_flag;
} cl_options;

/* private function prototypes */
void printusage(const char *progname);
int doScan(FILE *fp_ac, FILE *fp_cc,FILE *fpout_ac, FILE *fpout_cc,int scan,Header *header, InpConfig *inps, uvdata *data);
void parse_cmdline(const int argc, char * const argv[], const char *optstring);
int applyHeader(Header *header, uvdata *data);
void checkInputs(Header *header,uvdata *data,InpConfig *inputs);

/* allow convutils to use same file handle */
FILE *fpd=NULL;

/* private global vars */
static int bl_ind_lookup[MAX_ANT][MAX_ANT];
static int debug=0,lock_pointing=0;
static int pol_index[4];
static cl_options options;

/************************
************************/
int main(const int argc, char * const argv[]) {
  const char optstring[] = "vldS:a:c:o:I:H:A:F:s:";
  FILE *fpin_ac=NULL,*fpin_cc=NULL,*fpout_cc=NULL,*fpout_ac=NULL;
  int scan=0,res=0;
  Header header;
  InpConfig inputs;
  uvdata *data;
  array_data *arraydat;
  ant_table *antennas;

  fpd=stderr;
  memset(&options,'\0',sizeof(cl_options));
  options.stationfilename="antenna_locations.txt";
  options.configfilename="instr_config.txt";
  options.header_filename="header.txt";
  options.arr_lat_rad=MWA_LAT*(M_PI/180.0);
  options.arr_lon_rad=MWA_LON*(M_PI/180.0);
  options.height=MWA_HGT;
  options.do_flag=0;

  if(argc < 2) printusage(argv[0]);
  parse_cmdline(argc,argv,optstring);
  setConvDebugLevel(debug);

  /* initialise some values for the UV data array and antennas*/
  data = calloc(1,sizeof(uvdata));
  arraydat = calloc(1,sizeof(array_data));
  antennas = calloc(MAX_ANT,sizeof(ant_table));
  assert(antennas!=NULL && arraydat!=NULL && data != NULL);

  arraydat->antennas = antennas;
  arraydat->arr_lat_rad = options.arr_lat_rad;
  arraydat->arr_lon_rad = options.arr_lon_rad;

  /* get the mapping of inputs to anntena numbers and polarisations */
  if ((res = readInputConfig(options.configfilename, &inputs)) != 0) {
      fprintf(stderr,"readInputConfig failed with code %d. exiting\n",res);
  }

  /* get the number of antennas and their locations relative to the centre of the array */
  if ((res = readArray(options.stationfilename, options.arr_lat_rad, options.arr_lon_rad, arraydat)) != 0) {
      fprintf(stderr,"readArray failed with code %d. exiting\n",res);
  }

  /* read the header/metadata  */
  res = readHeader(options.header_filename,&header);
  if (res != 0) {
    fprintf(stderr,"Error reading main header. exiting.\n");
    exit(1);
  }

  checkInputs(&header,data,&inputs);

  /* open input files */
  if (header.corr_type!='A' && (fpin_cc=fopen(options.crosscor_filename,"r"))==NULL) {
    fprintf(stderr,"cannot open cross correlation input file <%s>\n",options.crosscor_filename);
    exit(1);
  }
  if (header.corr_type!='C' && (fpin_ac=fopen(options.autocorr_filename,"r"))==NULL) {
    fprintf(stderr,"cannot open auto correlation input file <%s>\n",options.autocorr_filename);
    exit(1);
  }

  /* open output files */
  if (header.corr_type != 'A' && (fpout_cc=fopen(options.outccfilename,"wb"))==NULL) {
    fprintf(stderr,"cannot open cross correlation output file <%s>\n",options.outccfilename);
    exit(1);
  }
  if (header.corr_type != 'C' && (fpout_ac=fopen(options.outacfilename,"wb"))==NULL) {
    fprintf(stderr,"cannot open auto correlation output file <%s>\n",options.outacfilename);
    exit(1);
  }

  /* assign vals to output data structure from inputs */
  res = applyHeader(&header, data);

  /* populate antenna info */
  if (debug) fprintf(fpd,"there are %d antennas\n",arraydat->n_ant);

  /* assign XYZ positions of the array for the site. */
  Geodetic2XYZ(arraydat->arr_lat_rad,arraydat->arr_lon_rad,options.height,
                &(arraydat->xyz_pos[0]),&(arraydat->xyz_pos[1]),&(arraydat->xyz_pos[2]));
  if (debug) fprintf(fpd,"converted array location to XYZ\n");

  /* create correlator->baseline mapping lookup table */
  assert(makeBaselineLookup(&inputs, &header, data->array, bl_ind_lookup)==0);

  /* read each scan, populating the data structure. */
  scan=0;
  while ((res = doScan(fpin_ac,fpin_cc,fpout_ac,fpout_cc,scan, &header, &inputs,data))==0) {

    if (options.flagfilename != NULL) {
      if (debug) fprintf(fpd,"Applying flags...\n");
      res = applyFlagsFile(options.flagfilename,data);
      if(res!=0) {
        fprintf(stderr,"Problems in applyFlagsFile. exiting\n");
        exit(1);
      }
    }
  }
  if(res < 0) {
      fprintf(stderr,"Problems in readScan(). exiting\n");
      exit(1);
  }

  if (debug) fprintf(fpd,"Read %d time steps\n",scan);
  if (abs(header.n_scans-scan) > 4) {
    fprintf(stderr,"WARNING: expected to read %d scans, but actually read %d. Are you sure you have the correct number of freqs, inputs and timesteps? Carrying on and hoping for the best...\n",header.n_scans,scan);
  }
  else if (res > 0) {
      fprintf(stderr,"WARNING: Wanted to read %d time steps, but actually read %d. Carrying on...\n",header.n_scans, scan);
  }

  /* finish up  */
  if(fpin_ac !=NULL) fclose(fpin_ac);
  if(fpin_cc !=NULL) fclose(fpin_cc);
  if(fpout_ac !=NULL) fclose(fpout_ac);
  if(fpout_cc !=NULL) fclose(fpout_cc);

  freeUVFITSdata(data);

  return 0;
}


/***************************
 ***************************/
int doScan(FILE *fp_ac, FILE *fp_cc,FILE *fpout_ac, FILE *fpout_cc,int scan_count, Header *header, InpConfig *inps,uvdata *uvdata) {

  static int init=0;
  //static float vis_weight=1.0;
  static double date_zero=0.0;  // time of zeroth scan

  double mjd;
  int res=0,n_read,scan=0;
  size_t size_ac, size_cc;
  float *ac_data=NULL;
  float complex *cc_data=NULL;
  array_data *array;

  array = uvdata->array;
  /* allocate space to read 1 time step of binary correlation data.
    There are n_inputs*nchan floats of autocorrelations per time step 
    and n_inp*(n_inp-1)/2*nchan float complex cross correlations*/
  size_ac = header->n_chans*header->n_inputs*sizeof(float);
  size_cc = header->n_chans*header->n_inputs*(header->n_inputs-1)/2*sizeof(float complex);
  ac_data = calloc(1,size_ac);
  cc_data = calloc(1,size_cc);
  assert(ac_data != NULL);
  assert(cc_data != NULL);

  if (!init) {
    /* count the total number of antennas actually present in the data */
    if (debug) fprintf(fpd,"Init %s.\n",__func__);
    /* set a weight for the visibilities based on integration time */
//    if(header->integration_time > 0.0) vis_weight = header->integration_time;

    date_zero = uvdata->date[0];    // this is already initialised in applyHeader

    init=1;
  }

  /* read all the data for this timestep */
  n_read = fread(cc_data,size_cc,1,fp_cc);
  if (n_read != 1) {
    fprintf(stderr,"EOF: reading cross correlations. Wanted to read %d bytes.\n",(int) size_cc);
    return 1;
  }
  n_read = fread(ac_data,size_ac,1,fp_ac);
  if (n_read != 1) {
    fprintf(stderr,"EOF: reading auto correlations. Wanted to read %d bytes.\n",(int) size_ac);
    return 1;
  }

  /* set time of scan. Note that 1/2 scan time offset already accounted for in date[0]. */
  if (scan_count > 0) uvdata->date[scan] = date_zero + scan_count*header->integration_time/86400.0;
  mjd = uvdata->date[scan] - 2400000.5;  // get Modified Julian date of scan.

  /* set default ha/dec from header, if HA was specified. Otherwise, it will be calculated below */
  if (lock_pointing!=0) {   // special case for RTS output which wants a phase centre fixed at an az/el, not ra/dec
    mjd = date_zero - 2400000.5;  // get Modified Julian date of scan.
  }

  /* apply geometric and/or cable length corrections to the visibilities */
  res = correctPhases(mjd, header, inps, array, bl_ind_lookup, ac_data, cc_data);
  if (res) return res;

  /* write the data back out again */
  n_read = fwrite(cc_data,size_cc,1,fpout_cc);
  if (n_read != 1) {
    fprintf(stderr,"%s: Failed to write cross correlations of size %d\n",__func__,(int)size_cc);
    return 1;
  }
  n_read = fwrite(ac_data,size_ac,1,fpout_ac);
  if (n_read != 1) {
    fprintf(stderr,"%s: Failed to write auto correlations of size %d\n",__func__,(int)size_ac);
    return 1;
  }

  if (ac_data != NULL) free(ac_data);
  if (cc_data != NULL) free(cc_data);
  return 0;
}


/****************************
*****************************/
void parse_cmdline(const int argc,char * const argv[], const char *optstring) {
    int result=0;
    char arrayloc[80],*lon,*lat;

    arrayloc[0]='\0';

    while ( (result = getopt(argc, argv, optstring)) != -1 ) {
        switch (result) {
          case 'S': options.stationfilename = optarg;
            break;
          case 'o': options.outccfilename = optarg;
            break;
          case 's': options.outacfilename = optarg;
            break;
          case 'a': options.autocorr_filename = optarg;
            break;
          case 'c': options.crosscor_filename = optarg;
            break;
          case 'd': debug = 1;
            fprintf(fpd,"Debugging on...\n");
            break;
          case 'I': options.configfilename = optarg;
            break;
          case 'H': options.header_filename = optarg;
            break;
          case 'F': options.flagfilename=optarg;
            break;
          case 'l': lock_pointing=1;
            fprintf(fpd,"Locking phase center to initial HA/DEC\n");
            break;
          case 'A':
            strncpy(arrayloc,optarg,80);
            break;
          case 'v':
            fprintf(stdout,"corr2uvfits revision $Rev: 4135 $\n");
            exit(1);
            break;
          default:
              fprintf(stderr,"unknown option: %c\n",result);
              printusage(argv[0]);
        }
    }

    /* convert array lon/lat */
    if(arrayloc[0]!='\0') {
        lon = arrayloc;
        lat = strpbrk(arrayloc,",");
        if (lat ==NULL) {
            fprintf(stderr,"Cannot find comma separator in lon/lat. Typo?\n");
            printusage(argv[0]);
        }
        /* terminate string for lon, then offset for lat */
        *lat = '\0';
        lat++;
        options.arr_lat_rad = atof(lat);    /* convert string in degrees to float */
        options.arr_lon_rad = atof(lon);
        fprintf(fpd,"User specified array lon,lat: %g, %g (degs)\n",options.arr_lon_rad,options.arr_lat_rad);
        options.arr_lat_rad *= (M_PI/180.0); // convert to radian
        options.arr_lon_rad *= (M_PI/180.0);
    }

    /* auto flagging requires autocorrelations */
    if (options.autocorr_filename==NULL && options.do_flag) {
        fprintf(stderr,"ERROR: auto flagging requires the autocorrelations to be used\n");
        exit(1);
    }
}


/***************************
 ***************************/
void printusage(const char *progname) {
  fprintf(stderr,"Usage: %s [options]\n\n",progname);
  fprintf(stderr,"options are:\n");
  fprintf(stderr,"-a filename\tThe name of the input autocorrelation data file. no default.\n");
  fprintf(stderr,"-c filename\tThe name of the input cross-correlation data file. no default.\n");
  fprintf(stderr,"-o filename\tThe name of the output cross correlation file. No default.\n");
  fprintf(stderr,"-s filename\tThe name of the output auto (self) correlation file. No default.\n");
  fprintf(stderr,"-S filename\tThe name of the file containing antenna name and local x,y,z. Default: %s\n",
                    options.stationfilename);
  fprintf(stderr,"-I filename\tThe name of the file containing instrument config. Default: %s\n",options.configfilename);
  fprintf(stderr,"-H filename\tThe name of the file containing observing metadata. Default: %s\n",options.header_filename);
  fprintf(stderr,"-A lon,lat \tSpecify East Lon and Lat of array center (degrees). Comma separated, no spaces. Default: MWA\n");
  fprintf(stderr,"-l         \tLock the phase center to the initial HA/DEC\n");
  fprintf(stderr,"-F filename\tOptionally apply global flags as specified in filename.\n");
  fprintf(stderr,"-d         \tturn debugging on.\n");
  fprintf(stderr,"-v         \treturn revision number and exit.\n");
  exit(1);
}


/***********************
***********************/
int applyHeader(Header *header, uvdata *data) {

  double jdtime_base=0,mjd,lmst;
  int n_polprod=0,i,res;

  data->n_freq = header->n_chans;
  data->cent_freq = header->cent_freq*1e6;
  data->freq_delta = header->bandwidth/(header->n_chans)*1e6*(header->invert_freq ? -1.0: 1.0);
  strncpy(data->array->name,header->telescope,SIZ_TELNAME);
  strncpy(data->array->instrument,header->instrument,SIZ_TELNAME);

  /* discover how many pol products there are */
  createPolIndex(header->pol_products, pol_index);
  for(i=0; i<4; i++) if (header->pol_products[2*i] !='\0') n_polprod++;
  if(n_polprod<1 || n_polprod > 4) {
    fprintf(stderr,"bad number of stokes: %d\n",n_polprod);
    exit(1);
  }
  data->n_pol = n_polprod;

  /* set the polarisation product type. linear, circular or stokes */
  if (toupper(header->pol_products[0]) == 'X' || toupper(header->pol_products[0]) == 'Y') data->pol_type=-5;
  if (toupper(header->pol_products[0]) == 'R' || toupper(header->pol_products[0]) == 'L') data->pol_type=-1;
  if (debug) fprintf(fpd,"Found %d pol products. pol_type is: %d\n",n_polprod,data->pol_type);

  /* calculate the JD of the beginning of the data */
  slaCaldj(header->year, header->month, header->day, &jdtime_base, &res); // get MJD for calendar day of obs
  jdtime_base += 2400000.5;  // convert MJD to JD
  jdtime_base += header->ref_hour/24.0+header->ref_minute/1440.0+header->ref_second/86400.0; // add intra-day offset
  data->date[0] = jdtime_base+0.5*(header->integration_time/86400.0);
  if (debug) fprintf(fpd,"JD time is %.2lf\n",jdtime_base);

  memset(data->source->name,0,SIZE_SOURCE_NAME+1);
  strncpy(data->source->name,header->field_name,SIZE_SOURCE_NAME);

  mjd = data->date[0] - 2400000.5;  // get Modified Julian date of scan.
  lmst = slaRanorm(slaGmst(mjd) + options.arr_lon_rad);  // local mean sidereal time, given array location

  /* if no RA was specified in the header,then calculate the RA based on lmst and array location
     and update the ra */
  if (header->ra_hrs < -98.0 ) {
    // set the RA to be for the middle of the scan
//    header->ra_hrs = lmst*(12.0/M_PI) - header->ha_hrs_start + header->n_scans*header->integration_time*1.00274/(3600.0*2);   // include 1/2 scan offset
    header->ra_hrs = lmst*(12.0/M_PI) - header->ha_hrs_start;  // match existing code. RA defined at start of scan
    if (debug) fprintf(fpd,"Calculated RA_hrs: %g of field centre based on HA_hrs: %g and lmst_hrs: %g\n",
                        header->ra_hrs,header->ha_hrs_start,lmst*(12.0/M_PI));
  }

  /* extract RA, DEC from header. Beware negative dec and negative zero bugs. */
  data->source->ra  = header->ra_hrs;
  data->source->dec = header->dec_degs;

  /* calcualte the number of baselines, required to be constant for all data */
  data->n_baselines[0] = (data->array->n_ant)*(data->array->n_ant+1)/2; //default: both auto and cross
  if (header->corr_type=='A') data->n_baselines[0] = data->array->n_ant;
  if (header->corr_type=='C') data->n_baselines[0] = data->array->n_ant*(data->array->n_ant-1)/2;
  if (debug) fprintf(fpd,"Corr type %c, so there are %d baselines\n",header->corr_type,data->n_baselines[0]);

  return 0;
}


/**************************
***************************/
void checkInputs(Header *header,uvdata *data,InpConfig *inputs) {
    int total_ants;

    if(inputs->n_inputs != header->n_inputs) {
        fprintf(stderr,"%s ERROR: mismatch between the number of inputs in %s (%d) and header (%d)\n",__func__,
                options.configfilename,inputs->n_inputs,header->n_inputs);
        exit(1);
    }

    total_ants = countPresentAntennas(inputs);

    if (total_ants > data->array->n_ant) {
        fprintf(stderr,"ERROR: mismatch between the number of antennas in %s (%d) and %s (%d)\n",
                options.stationfilename,data->array->n_ant,options.configfilename,total_ants);
    }
    
    if ((options.crosscor_filename==NULL || options.outccfilename==NULL) && 
        (header->corr_type == 'C' || header->corr_type=='B')) {
        fprintf(stderr,"ERROR: must specify an input and output cross correlation file for type '%c'\n",header->corr_type);
        exit(1);
    }
    if ((options.autocorr_filename==NULL || options.outacfilename==NULL) && 
        (header->corr_type == 'A' || header->corr_type=='B')) {
        fprintf(stderr,"ERROR: must specify an input and output auto correlation file for type '%c'\n",header->corr_type);
        exit(1);
    }
    if (header->ha_hrs_start == -99.0 && lock_pointing) {
        fprintf(stderr,"ERROR: HA must be specified in header if -l flag is used.\n");
        exit(1);
    }

}

