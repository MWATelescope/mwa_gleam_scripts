/* Program to convert the binary output format of the 32T on-site correlators
 * UV FITS format. Written by Randall Wayth. Feb, 2008.
 *
 * August 12, 2011 - precess u, v, w, data to J2000 frame (Alan Levine)
$Rev: 4135 $:     Revision of last commit
$Author: rwayth $:  Author of last commit
$Date: 2011-10-18 22:53:40 +0800 (Tue, 18 Oct 2011) $:    Date of last commit
*/

#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <complex.h>
#include <math.h>
#include <ctype.h>
#include <fitsio.h>
#include "slalib.h"
#include "uvfits.h"

#define MAX_ANT 32
#define MAX_BASELINES (MAX_ANT*(MAX_ANT+1)/2) // including autocorrelations 
#define MAX_LINE 1024
#define MWA_LAT -26.703319        // Array latitude. degrees North
#define MWA_LON 116.67081         // Array longitude. degrees East
#define MWA_HGT 377               // Array altitude. meters above sea level
#define EARTH_RAD 6378100.0       // meters
#define SIZ_PRODNAME 8            // size of char array with text type of pol products.
#define VLIGHT 299792458.0        // speed of light. m/s
#define AUTOFLAG_N_NEIGHBOURS 2   // number of neighbours to use to form a median for channel flagging.

#define CHAN_ALL_ANT_ALL_TIME      "CHAN_ALL_ANT_ALL_TIME"

typedef struct _header {
    int     n_inputs;               // the number of inputs to the corrleator
    int        n_scans;                // the number of time samples
    int        n_chans;                // the number of spectral channels
    int     corr_type;              // cross correlation, auto or both 'C', 'A', 'B'
    int     invert_freq;            // flag to indicate that freq decreases with increasing channel number.
    int     conjugate;              // conjugate the final vis to correct for any sign errors
    int     geom_correct;           // apply geometric phase correction
    float   integration_time;        // per time sample, in seconds
    double  cent_freq,bandwidth;    // observing central frequency and bandwidth (MHz)
    double  ra_hrs,dec_degs;        // ra,dec of phase centre.
    double  ha_hrs_start;           // the HA of the phase center at the start of the integration
    double  ref_el,ref_az;          // the el/az of the normal to the plane of the array (radian)
    int     year,month,day;            // date/time in UTC.
    int     ref_hour,ref_minute;
    float   ref_second;
    char    field_name[SIZE_SOURCE_NAME+1];
    char    pol_products[SIZ_PRODNAME+1];
} Header;

typedef struct {
    int n_inputs;
    int ant_index[MAX_ANT*2];
    float cable_len_delta[MAX_ANT*2];
    char pol_index[MAX_ANT*2];
    char inpFlag[MAX_ANT*2];
} InpConfig;


/* private function prototypes */
void printusage(const char *progname);
int readScan(FILE *fp_ac, FILE *fp_cc,int scan,Header *header, InpConfig *inps,uvdata *data);
int createPolIndex(char *polprods, int *index);
int readArray(char *filename, double lat, ant_table *data, int *nants);
void parse_cmdline(const int argc, char * const argv[], const char *optstring);
int readHeader(char *filename, Header *header);
void initData(uvdata *data);
int applyHeader(Header *header, uvdata *data);
int readInputConfig(char *filename, InpConfig *inp);
void calcUVW(double ha,double dec,double x,double y,double z,double *u,double *v,double *w);
void checkInputs(Header *header,uvdata *data,InpConfig *inputs);
int decodePolChar(int pol_char);
int decodePolIndex(int pol1, int pol2);
void azel2xyz(double az, double el, double *x, double *y, double *z);
int qsort_compar_float(const void *p1, const void *p2);
int autoFlag(uvdata *uvdata, float sigma, int n_neighbours);
int flag_antenna(uvdata *uvdata, const int ant, const int pol, const int chan, const int t);
int flag_all_antennas(uvdata *uvdata, const int chan, const int t);
int applyFlagsFile(char *flagfilename,uvdata *uvdata);
int countPresentAntennas(InpConfig *inputs);
int checkAntennaPresent(InpConfig *inputs, int ant_index);
void precXYZ(double rmat[3][3], double x, double y, double z, double lmst,
         double *xp, double *yp, double *zp, double lmst2000);
void rotate_radec(double rmat[3][3], double ra1, double dec1,
          double *ra2, double *dec2);
void aber_radec_rad(double eq, double mjd, double ra1, double dec1,
            double *ra2, double *dec2);
void stelaber(double eq, double mjd, double v1[3], double v2[3]);
void mat_transpose(double rmat1[3][3], double rmat2[3][3]);
void unitvecs_j2000(double rmat[3][3], double xhat[3], double yhat[3], double zhat[3]);
void ha_dec_j2000(double rmat[3][3], double lmst, double lat_rad, double ra2000,
                  double dec2000, double *newha, double *newlat, double *newlmst);

/* private global vars */
int debug=0,do_flag=0,debug_flag=0,lock_pointing=0;
int pol_index[4];
FILE *fpd=NULL;
char *stationfilename="antenna_locations.txt",*outfilename=NULL;
char *configfilename="instr_config.txt";
char *header_filename="header.txt";
char *crosscor_filename=NULL;
char *autocorr_filename=NULL;
char *flagfilename=NULL;
double arr_lat_rad=MWA_LAT*(M_PI/180.0),arr_lon_rad=MWA_LON*(M_PI/180.0),height=MWA_HGT;

/************************
************************/
int main(const int argc, char * const argv[]) {
  const char optstring[] = "vldS:a:c:o:I:H:A:F:f:";
  FILE *fpin_ac=NULL,*fpin_cc=NULL;
  int i,scan=0,res=0;
  Header header;
  InpConfig inputs;
  uvdata data;
  array_data arraydat;
  source_table source;
  ant_table *antennas;

  fpd=stdout;

  if(argc < 2) printusage(argv[0]);
  parse_cmdline(argc,argv,optstring);

  /* initialise some values for the UV data array and antennas*/
  antennas = calloc(MAX_ANT,sizeof(ant_table));
  if(antennas==NULL) {
    fprintf(stderr,"no malloc for antenans\n");
    exit(1);
  }
  data.antennas = antennas;
  data.array    = &arraydat;
  data.source   = &source;
  initData(&data);

  /* get the mapping of inputs to anntena numbers and polarisations */
  if ((res = readInputConfig(configfilename, &inputs)) != 0) {
      fprintf(stderr,"readInputConfig failed with code %d. exiting\n",res);
  }

  /* get the number of antennas and their locations relative to the centre of the array */
  if ((res = readArray(stationfilename, arr_lat_rad, antennas,&arraydat.n_ant)) != 0) {
      fprintf(stderr,"readArray failed with code %d. exiting\n",res);
  }

  /* read the header/metadata  */
  res = readHeader(header_filename,&header);
  if (res != 0) {
    fprintf(stderr,"Error reading main header. exiting.\n");
    exit(1);
  }

  checkInputs(&header,&data,&inputs);

  /* open input files */
  if (header.corr_type!='A' && (fpin_cc=fopen(crosscor_filename,"r"))==NULL) {
    fprintf(stderr,"cannot open cross correlation input file <%s>\n",crosscor_filename);
    exit(1);
  }
  if (header.corr_type!='C' && (fpin_ac=fopen(autocorr_filename,"r"))==NULL) {
    fprintf(stderr,"cannot open auto correlation input file <%s>\n",autocorr_filename);
    exit(1);
  }

  /* assign vals to output data structure from inputs */
  res = applyHeader(&header, &data);

  /* populate antenna info */
  if (debug) fprintf(fpd,"there are %d antennas\n",arraydat.n_ant);
  for (i=0; i<arraydat.n_ant; i++){
    //sprintf(antennas[i].name,"ANT%03d",i+1);
    // FIXME: update this for correct pol type
    sprintf(antennas[i].pol_typeA,"X");
    sprintf(antennas[i].pol_typeB,"Y");
    antennas[i].pol_angleA = 0.0;
    antennas[i].pol_angleB = 90.0;
    antennas[i].pol_calA = 0.0;
    antennas[i].pol_calB = 0.0;
    antennas[i].mount_type = 0;
  }

  /* assign XYZ positions of the array for the site. */
  /* NOTE: this is correct only for geocentric lat/lon. Should use the 
  arraydat.xyz_pos[0] = (EARTH_RAD+height)*cos(arr_lat_rad)*cos(arr_lon_rad);
  arraydat.xyz_pos[1] = (EARTH_RAD+height)*cos(arr_lat_rad)*sin(arr_lon_rad);
  arraydat.xyz_pos[2] = (EARTH_RAD+height)*sin(arr_lat_rad);
  SLA_GEOC function to calculate proper geodetic to geocentric conversion otherwise */
  Geodetic2XYZ(arr_lat_rad,arr_lon_rad,height,&(arraydat.xyz_pos[0]),&(arraydat.xyz_pos[1]),&(arraydat.xyz_pos[2]));

  /* read each scan, populating the data structure. */
  for (scan=0; scan < header.n_scans; scan++) {
    res = readScan(fpin_ac,fpin_cc,scan, &header, &inputs, &data);
    if(res!=0) {
      fprintf(stderr,"Problems in readScan(). exiting\n");
      exit(1);
    }
  }

  if (do_flag) {
    if (debug) fprintf(fpd,"Auto flagging...\n");
    res = autoFlag(&data,5.0,AUTOFLAG_N_NEIGHBOURS);
    if(res!=0) {
      fprintf(stderr,"Problems in autoflag. exiting\n");
      exit(1);
    }
  }

  if (flagfilename != NULL) {
    res = applyFlagsFile(flagfilename,&data);
    if(res!=0) {
      fprintf(stderr,"Problems in applyFlagsFile. exiting\n");
      exit(1);
    }
  }

  if (debug){
    fprintf(fpd,"writing the UVFITS file\n");
    fprintf(fpd,"there are %d time sets of visibilities with %d baselines\n",data.n_vis,data.n_baselines[0]);
  }

  /* we now have all the data, write it out */
  writeUVFITS(outfilename,&data);

  if(debug) fprintf(fpd,"finished writing UVFITS file\n");
  if(fpin_ac !=NULL) fclose(fpin_ac);
  if(fpin_cc !=NULL) fclose(fpin_cc);
  return 0;
}


/* simple median-based flagging based on autocorrelations */
/* to avoid making an additional copy of all the data, which needs to be sorted,
   we pass through the data once for each ant/pol combination
   and extract the data vs time for each single channel. This is then sorted by magnitude
   per channel and the variance estimate made. */
int autoFlag(uvdata *uvdata, float sigma, int n_neighbours) {
    int status=0,ant,pol,chan,t,bl,ant1,ant2,visindex;
    float *chan_sigma=NULL, *chan_data=NULL, *chan_median=NULL, *chan_sorted=NULL, sig, med;
    char  *flags=NULL;
    float local_medians[AUTOFLAG_N_NEIGHBOURS*2+1],local_stdevs[AUTOFLAG_N_NEIGHBOURS*2+1];
    
    /* init */
    chan_sigma    = calloc(uvdata->n_freq, sizeof(float));
    chan_median   = calloc(uvdata->n_freq, sizeof(float));
    chan_data     = malloc(uvdata->n_vis*uvdata->n_freq*sizeof(float));
    chan_sorted   = malloc(uvdata->n_vis*uvdata->n_freq*sizeof(float));
    flags         = malloc(uvdata->n_vis*uvdata->n_freq*sizeof(char));
    if(chan_sigma ==NULL || chan_data==NULL || chan_median==NULL || flags ==NULL || chan_sorted==NULL) {
        fprintf(stderr,"ERROR: autoFlag: no malloc\n");
        exit(1);
    }


    /* each pol on each antenna is treated separately, then all baselines for affected visibilities for
       the ant/pol are flagged */
    for(ant=1; ant <= uvdata->array->n_ant; ant++) {
    for(pol=0; pol < (int)ceil(uvdata->n_pol/2.0); pol++) {
        // make pass through data to determine variance estimates
        for(bl=0; bl < uvdata->n_baselines[0]; bl++) {
           // is this the autocorrelation we're looking for?
           DecodeBaseline(uvdata->baseline[0][bl], &ant1, &ant2);
           for(t=0; t<uvdata->n_vis; t++) {
                for(chan=0; chan < uvdata->n_freq; chan++) {
                   if( ant1 == ant2 && ant1 == ant) {
                        // extract data for this time,pol,channel
                        visindex = bl*uvdata->n_pol*uvdata->n_freq + chan*uvdata->n_pol + pol;
                        chan_data[chan*uvdata->n_vis + t] = uvdata->visdata[t][visindex*2];
                    }
                }
            }
        }
        // make a copy of the data that will be sorted
        memcpy(chan_sorted,chan_data,uvdata->n_vis*uvdata->n_freq*sizeof(float));
        for(chan=0; chan < uvdata->n_freq; chan++) {
            /* sort the data by magnitude */
            qsort(chan_sorted+chan*uvdata->n_vis,uvdata->n_vis,sizeof(float),qsort_compar_float);
            /* estimate channel variance based on interquartile range . ((d[0.75*n_vis] - d[0.25*n_vis])/1.35)^2*/
            sig = ( (chan_sorted[(int)(chan*uvdata->n_vis+0.75*uvdata->n_vis)]-chan_sorted[(int)(chan*uvdata->n_vis+0.25*uvdata->n_vis)])/1.35);
            med = chan_sorted[(int)(chan*uvdata->n_vis + 0.5*uvdata->n_vis)];
            chan_sigma[chan]  = fabs(sig);
            chan_median[chan] = med;
            if(debug_flag) fprintf(fpd,"ant: %d, pol: %d, chan: %d. Median: %g, stddev: %g\n",ant,pol,chan,med,sig);
        }

        /* next pass through data to apply flags */
        /* clear existing flags */
        memset(flags,'\0',uvdata->n_vis*uvdata->n_freq);
        for(chan=0; chan < uvdata->n_freq; chan++) {
            int lower,upper,n_points,in_flag;
            float local_median,local_stdev,val;
            // set bounds for lower and upper chans for neighbor comparisions
            lower = chan-n_neighbours;
            if (lower < 0) lower=0;
            upper = chan+n_neighbours;
            if (upper >= uvdata->n_freq) upper = uvdata->n_freq-1;
            switch(do_flag) {
                case 1:
                    // generic case - don't do anything special
                    break;
                case 2: {
                    int n_rej = 6;
                    // MWA 40kHz channels. do not use the n_rej edge channels to compare to neighbours
                    // there are 32 fine 40kHz channels per coarse 1.28MHz channel. So we ignore the edge
                    // channels within a coarse chan
                    if (chan%32 <= n_rej || chan%32 > 32-n_rej) lower = upper = chan;
                    if (chan%32 > n_rej && lower%32 < n_rej) lower += n_rej-lower%32;
                    if (chan%32 < 32-n_rej && upper%32 >= 32-n_rej) upper -= (upper%32)-(31-n_rej);
                    break;
                    }
                case 3:
                default:
                    fprintf(stderr,"Unsupported/unknown autoflag mode %d. Not flagging\n",do_flag);
                    goto EXIT;
            }
            n_points = upper-lower+1;
            // extract median and stdev channel values for channel plus neighbours. By using the neighbours, we avoid
            // being contaminated by long-lived, narrowband RFI.
            memcpy(local_medians,chan_median+lower,sizeof(float)*n_points);
            memcpy(local_stdevs,chan_sigma+lower,sizeof(float)*n_points);
            // sort the local medians and stdevs to get the median of medians and median of stdevs
            qsort(local_medians,n_points,sizeof(float),qsort_compar_float);
            qsort(local_stdevs,n_points,sizeof(float),qsort_compar_float);
            // use the local median,stdev as the median,stdev for this channel
            local_median = local_medians[n_points/2];
            local_stdev  = local_stdevs[n_points/2];
            if(debug_flag) fprintf(fpd,"ant: %d, pol: %d, chan: %d. Local median: %g, local stdev: %g\n",ant,pol,chan,local_median,local_stdev);
            // now scan data to find outliers and flag them
            in_flag=0;
            for(t=0; t<uvdata->n_vis; t++) {
                val = chan_data[chan*uvdata->n_vis + t];
                if ( fabs(val - local_median) > sigma*local_stdev) {
                    if(debug_flag) fprintf(fpd,"flagging ant: %d, pol: %d, chan: %d, time: %d. Val: %g\n",ant,pol,chan,t,val);
                    flag_antenna(uvdata,ant,pol,chan,t);
                    flags[chan + t*uvdata->n_freq] = 1;
                }
            }
        }
        // make an image of the flags for this input (for debugging purposes)

        if (debug_flag) {
            char filename[100];
            long fpixel[2];
            fitsfile *fp=NULL;
            //dump flags
            sprintf(filename,"flags_inp%02d_pol%d.fits",ant,pol);
            remove(filename);
            fits_create_file(&fp,filename,&status);
            if (status !=0) {
                fprintf(stderr,"autoFlag: cannot create file %s\n",filename);
                return 1;
            }
            fprintf(fpd,"created flag dump file %s\n",filename);
            fpixel[0] = uvdata->n_freq;
            fpixel[1] = uvdata->n_vis;
            fits_create_img(fp, BYTE_IMG, 2, fpixel, &status);
            fpixel[0] = 1;
            fpixel[1] = 1;
            fits_write_pix(fp, TBYTE, fpixel, uvdata->n_freq*uvdata->n_vis,flags, &status);
            fits_close_file(fp,&status);
            // dump data
            sprintf(filename,"data_inp%02d_pol%d.fits",ant,pol);
            remove(filename);
            fits_create_file(&fp,filename,&status);
            if (status !=0) {
                fprintf(stderr,"autoFlag: cannot create file %s\n",filename);
                return 1;
            }
            fprintf(fpd,"created flag dump file %s\n",filename);
            fpixel[1] = uvdata->n_freq;
            fpixel[0] = uvdata->n_vis;
            fits_create_img(fp, FLOAT_IMG, 2, fpixel, &status);
            fpixel[0] = 1;
            fpixel[1] = 1;
            fits_write_pix(fp, TFLOAT, fpixel, uvdata->n_freq*uvdata->n_vis,chan_data, &status);
            fits_close_file(fp,&status);
        }

    }   
    }

EXIT:
    /* free working arrays */
    if (chan_sigma!= NULL) free(chan_sigma);
    if (chan_median!=NULL) free(chan_median);
    if (chan_data != NULL) free(chan_data);
    if (chan_sorted!=NULL) free(chan_sorted);
    if (flags != NULL)     free(flags);
    return status;
}


/* flag all antennas/pols for channel chan at time index t */
/* setting a visibility weight to negative means it is flagged */
int flag_all_antennas(uvdata *uvdata, const int chan, const int t) {
    int bl,pol,visindex;
    float weight;

    for (bl=0; bl<uvdata->n_baselines[t]; bl++) {
         for(pol=0; pol < uvdata->n_pol; pol++) {
            visindex = bl*uvdata->n_pol*uvdata->n_freq + chan*uvdata->n_pol + pol;
            weight = uvdata->weightdata[t][visindex];
            if (weight > 0) uvdata->weightdata[t][visindex] = -weight;
         }
    }
    return 0;
}


/* flag all visibilities that are formed by the antenna "ant" on polarisation "pol"
   in channel "chan" at time index "t".
*/
int flag_antenna(uvdata *uvdata, const int ant, const int pol, const int chan, const int t) {
    int bl,ant1,ant2,visindex;
    float weight;

    for (bl=0; bl<uvdata->n_baselines[t]; bl++) {
        // antenna we're looking for?
        DecodeBaseline(uvdata->baseline[t][bl], &ant1, &ant2);
        if (ant1 == ant || ant2==ant) {
            // negative weights mean flagged
            visindex = bl*uvdata->n_pol*uvdata->n_freq + chan*uvdata->n_pol + pol;
            weight = uvdata->weightdata[t][visindex];
            if (weight > 0) {
                uvdata->weightdata[t][visindex] = -weight;
            }
            // and the other product with this pol, if applicable
            if (uvdata->n_pol > 1) {
                visindex += 2;
                weight = uvdata->weightdata[t][visindex];
                if (weight > 0) {
                    uvdata->weightdata[t][visindex] = -weight;
                }
            }
        }  
    }
    return 0;
}


/* apply a simple global flags file to the data */
int applyFlagsFile(char *filename,uvdata *data) {
    FILE *fp=NULL;
    char line[MAX_LINE],key[80];
    int val;

    if ((fp=fopen(filename,"r")) ==NULL) {
        fprintf(stderr,"Cannot open flags file %s\n",filename);
        return 1;
    }
    if(debug) fprintf(fpd,"Applying global flags in flags file: %s\n",filename);

    /* process each line in the file */
    while( fgets(line,MAX_LINE,fp) != NULL) {
        /* skip comment and blank lines */
        if (line[0] == '\0' || line[0] == '\n' || line[0]=='#') continue;

        /* process the line */
        sscanf(line,"%s %d",key,&val);
        if (strncmp(CHAN_ALL_ANT_ALL_TIME,line,strlen(CHAN_ALL_ANT_ALL_TIME))==0) {
            int t;

            /* flag a channel for all antennas and times */
            /* check that channel is valid */
            if (val >= data->n_freq) {
                fprintf(stderr,"ERROR: asked to flag channel %d, but only have %d\n",val,data->n_freq);
                fprintf(stderr,"Offending line: %s\n",line);
            }
            if(debug) fprintf(fpd,"Flagging chan %d on all antennas\n",val);
            for (t=0; t<data->n_vis; t++) flag_all_antennas(data, val, t);
        }
    }

    if (fp !=NULL) fclose(fp);
    return 0;
}


/* comparison function for qsort in the autoflagger */
int qsort_compar_float(const void *p1, const void *p2) {
    float val1,val2;

    val1 = *((float *)p1);
    val2 = *((float *)p2);
    if (val1 < val2) return -1;
    if (val1 > val2) return 1;
    return 0;
}


/***************************
 ***************************/
int readScan(FILE *fp_ac, FILE *fp_cc,int scan, Header *header, InpConfig *inps, uvdata *uvdata) {

  double ha=0,mjd,lmst,ra_app,dec_app;
  double ant_u[MAX_ANT],ant_v[MAX_ANT],ant_w[MAX_ANT]; //u,v,w for each antenna, in meters
  double u,v,w,cable_delay=0;
  double x,y,z, xprec, yprec, zprec, rmatpr[3][3], rmattr[3][3];
  double lmst2000, ha2000, newarrlat, ant_u_ep, ant_v_ep, ant_w_ep;
  double ra_aber, dec_aber;
  int i,inp1,inp2,ant1,ant2,pol1,pol2,bl_index=0,visindex,pol_ind,chan_ind,n_read;
  int bl_ind_lookup[MAX_ANT][MAX_ANT],temp,baseline_reverse,total_ants;
  float *visdata=NULL,vis_weight=1.0;

  /* allocate space to read binary correlation data. Size is complex float * n_channels */
  visdata = malloc(2*sizeof(float)*uvdata->n_freq);
  if (visdata==NULL) {
      fprintf(stderr,"ERROR: no malloc for visdata array in readScan\n");
      exit(1);
  }

  /* count the total number of antennas actually present in the data */
  total_ants = countPresentAntennas(inps);

  /* make a lookup table for which baseline corresponds to a correlation product */
  if(header->corr_type=='A') {
      /* autocorrelations only */
      for(ant1=0; ant1 < uvdata->array->n_ant; ant1++) {
        if (checkAntennaPresent(inps,ant1) == 0) continue;
        if(debug) fprintf(fpd,"AUTO: bl %d is for ant %d\n",bl_index,ant1);
        bl_ind_lookup[ant1][ant1] = bl_index++;
    }
  }
  else if(header->corr_type=='C') {
      /* this for cross correlations only */
      for (ant1=0; ant1 < uvdata->array->n_ant-1; ant1++) {
        if (checkAntennaPresent(inps,ant1) == 0) continue;
          for(ant2=ant1+1; ant2 < uvdata->array->n_ant; ant2++) {
            if (checkAntennaPresent(inps,ant2) == 0) continue;
            if(debug) fprintf(fpd,"CROSS: bl %d is for ants %d-%d\n",bl_index,ant1,ant2);
              bl_ind_lookup[ant1][ant2] = bl_index++;
          }
      }
  }
  else {
      /* this for auto and cross correlations */
      for (ant1=0; ant1 < uvdata->array->n_ant; ant1++) {
        if (checkAntennaPresent(inps,ant1) == 0) continue;
          for(ant2=ant1; ant2 < uvdata->array->n_ant; ant2++) {
            if (checkAntennaPresent(inps,ant2) == 0) continue;
            if(debug) fprintf(fpd,"BOTH: bl %d is for ants %d-%d\n",bl_index,ant1,ant2);
              bl_ind_lookup[ant1][ant2] = bl_index++;
          }
      }
  }

  /* increase size of arrays for the new scan */
  uvdata->n_vis++;
  uvdata->date=realloc(uvdata->date,(scan+1)*sizeof(double));
  uvdata->visdata=realloc(uvdata->visdata,(scan+1)*sizeof(double *));
  uvdata->weightdata=realloc(uvdata->weightdata,(scan+1)*sizeof(double *));
  uvdata->u=realloc(uvdata->u,(scan+1)*sizeof(double *));
  uvdata->v=realloc(uvdata->v,(scan+1)*sizeof(double *));
  uvdata->w=realloc(uvdata->w,(scan+1)*sizeof(double *));
  uvdata->n_baselines = realloc(uvdata->n_baselines,(scan+1)*sizeof(int));
  uvdata->n_baselines[scan] = 0;
  uvdata->baseline = realloc(uvdata->baseline,(scan+1)*sizeof(float *));

  /* make space for the actual visibilities and weights */
  if (debug) fprintf(fpd,"callocing array of %d floats for scan %d\n",MAX_BASELINES*uvdata->n_freq*uvdata->n_pol*2,scan);
  uvdata->visdata[scan]    = calloc(MAX_BASELINES*uvdata->n_freq*uvdata->n_pol*2,sizeof(float));
  uvdata->weightdata[scan] = calloc(MAX_BASELINES*uvdata->n_freq*uvdata->n_pol  ,sizeof(float));
  uvdata->u[scan] = calloc(MAX_BASELINES,sizeof(double));
  uvdata->v[scan] = calloc(MAX_BASELINES,sizeof(double));
  uvdata->w[scan] = calloc(MAX_BASELINES,sizeof(double));
  uvdata->baseline[scan] = calloc(MAX_BASELINES,sizeof(float));
  if(uvdata->visdata[scan]==NULL || uvdata->weightdata[scan]==NULL || uvdata->visdata[scan]==NULL
     || uvdata->visdata[scan]==NULL || uvdata->visdata[scan]==NULL || uvdata->baseline[scan]==NULL) {
    fprintf(stderr,"readScan: no malloc for BIG arrays\n");
    exit(1);
  }
  
  /* set a weight for the visibilities based on integration time */
  if(header->integration_time > 0.0) vis_weight = header->integration_time;

  /* calc number of baselines depending on correlation product type(s) and how many antennas were active */
  uvdata->n_baselines[scan] = total_ants*(total_ants+1)/2; //default: both auto and cross
  if (header->corr_type=='A') uvdata->n_baselines[scan] = total_ants;
  if (header->corr_type=='C') uvdata->n_baselines[scan] = total_ants*(total_ants-1)/2;

  /* set time of scan. Note that 1/2 scan time offset already accounted for in date[0]. */
  if (scan > 0) uvdata->date[scan] = uvdata->date[0] + scan*header->integration_time/86400.0;

  /* set default ha/dec from header, if HA was specified. Otherwise, it will be calculated below */
  dec_app = header->dec_degs*(M_PI/180.0);
  if (lock_pointing==0) {
    ha = (header->ha_hrs_start+(scan+0.5)*header->integration_time/3600.0*1.00274)*(M_PI/12.0);
  } else {
    ha = (header->ha_hrs_start)*(M_PI/12.0);
  }

  mjd = uvdata->date[scan] - 2400000.5;  // get Modified Julian date of scan.
  lmst = slaRanorm(slaGmst(mjd) + arr_lon_rad);  // local mean sidereal time, given array location
    /* convert mean RA/DEC of phase center to apparent for current observing time. This applies precession,
       nutation, annual abberation. */
    slaMap(header->ra_hrs*(M_PI/12.0), header->dec_degs*(M_PI/180.0), 0.0, 0.0, 0.0, 0.0, 2000.0,
       mjd, &ra_app, &dec_app);
    if (debug) fprintf(fpd,"Precessed apparent coords (radian): RA: %g, DEC: %g\n",ra_app,dec_app);
    /* calc apparent HA of phase center, normalise to be between 0 and 2*pi */
    ha = slaRanorm(lmst - ra_app);

  /* I think this is correct - it does the calculations in the frame with current epoch 
  * and equinox, nutation, and aberrated star positions, i.e., the apparent geocentric
  * frame of epoch. (AML)
  */

    if(debug) fprintf(fpd,"scan %d. lmst: %g (radian). HA (calculated): %g (radian)\n",scan, lmst,ha);

  /* calc el,az of desired phase centre for debugging */
  if (debug) {
      double az,el;
      slaDe2h(ha,dec_app,arr_lat_rad,&az,&el);
      fprintf(fpd,"Phase cent ha/dec: %g,%g. az,el: %g,%g\n",ha,dec_app,az,el);
  }

  /* Compute the apparent direction of the phase center in the J2000 coordinate system */
  aber_radec_rad(2000.0,mjd,header->ra_hrs*(M_PI/12.0),header->dec_degs*(M_PI/180.0),
         &ra_aber,&dec_aber);

  /* Below, the routines "slaPrecl" and "slaPreces" do only a precession correction,
   * i.e, they do NOT do corrections for aberration or nutation.
   *
   * We want to go from apparent coordinates at the observation epoch
   * to J2000 coordinates which do not have the nutation or aberration corrections
   * (and since the frame is J2000 no precession correction is needed).
   */

  // slaPrecl(slaEpj(mjd),2000.0,rmatpr);  /* 2000.0 = epoch of J2000 */
  slaPrenut(2000.0,mjd,rmattr);
  mat_transpose(rmattr,rmatpr);
  /* rmatpr undoes precession and nutation corrections */
  ha_dec_j2000(rmatpr,lmst,arr_lat_rad,ra_aber,dec_aber,&ha2000,&newarrlat,&lmst2000);

  if (debug) {
    fprintf(fpd,"Dec, dec_app, newarrlat (radians): %f %f %f\n",
        header->dec_degs*(M_PI/180.0),dec_app,newarrlat);
    fprintf(fpd,"lmst, lmst2000 (radians): %f %f\n",lmst,lmst2000);
    fprintf(fpd,"ha, ha2000 (radians): %f %f\n",ha,ha2000);
  }
  /* calc u,v,w at phase center and reference for all antennas relative to center of array */
  for(i=0; i<uvdata->array->n_ant; i++) {
    // double x,y,z;   /* moved to front of this function (Aug. 12, 2011) */
      x = uvdata->antennas[i].xyz_pos[0];
      y = uvdata->antennas[i].xyz_pos[1];
      z = uvdata->antennas[i].xyz_pos[2];
      /* value of lmst at current epoch - will be changed to effective value in J2000 system 
       * 
       * To do this, need to precess "ra, dec" (in quotes on purpose) of array center
       * from value at current epoch 
       */
      precXYZ(rmatpr,x,y,z,lmst,&xprec,&yprec,&zprec,lmst2000);
      calcUVW(ha,dec_app,x,y,z,&ant_u_ep,&ant_v_ep,&ant_w_ep);
      calcUVW(ha2000,dec_aber,xprec,yprec,zprec,ant_u+i,ant_v+i,ant_w+i);
      if (debug) {
        /* The w value should be the same in either reference frame. */
          fprintf(fpd,"Ant: %d, u,v,w: %g,%g,%g.\n",i,ant_u[i],ant_v[i],ant_w[i]);
          fprintf(fpd,"Ant at epoch: %d, u,v,w: %g,%g,%g.\n",i,ant_u_ep,ant_v_ep,ant_w_ep);
      }
  }
 

  for(inp1=0; inp1 < header->n_inputs ; inp1++) {
    for(inp2=inp1; inp2 < header->n_inputs ; inp2++) {

        /* decode the inputs into antennas and pols */
        baseline_reverse=0;
        ant1 = inps->ant_index[inp1];
        ant2 = inps->ant_index[inp2];
        pol1 = inps->pol_index[inp1];
        pol2 = inps->pol_index[inp2];
        /* UVFITS by convention expects the index of ant2 to be greater than ant1, so swap if necessary */
        if (ant1>ant2) {
            temp=ant1;
            ant1=ant2;
            ant2=temp;
            temp=pol1;
            pol1=pol2;
            pol2=temp;
            baseline_reverse=1;
        }
        pol_ind = decodePolIndex(pol1, pol2);
        bl_index = bl_ind_lookup[ant1][ant2];
        
        /* cable delay: the goal is to *correct* for differential cable lengths. The inputs include a delta (offset)
           of cable length relative to some ideal length. (positive = longer than ideal)
           Call the dot product of the baseline (ant2-ant1) and look direction 'phi'.
           Then if ant1 has more delay than ant2, then this is like having phi be positive where
           the visibility is V = Iexp(-j*2*pi*phi)
           Hence we want to add the difference ant2-ant1 (in wavelengths) to phi to correct for the length difference.
           the magic 1.2 factor comes from the speed change of the electric field in the cables, such that
           the cables are electrically longer than they are physically. This is for RG6 coax.
         */
        cable_delay = (inps->cable_len_delta[inp2] - inps->cable_len_delta[inp1])*1.204;
        
        /* only process the appropriate correlations */
        if (header->corr_type=='A' && inp1!=inp2) continue;
        if (header->corr_type=='C' && inp1==inp2) continue;

        /* There is now one block of channels for each correlation product, read it. */
        if (inp1 != inp2) {
            /* read a block of cross-correlations */
            n_read = fread(visdata,sizeof(float)*2,uvdata->n_freq,fp_cc);
        }
        else {
            /* read a block of auto-correlations */
            n_read = fread(visdata,sizeof(float),uvdata->n_freq,fp_ac);
        }
        if (n_read != uvdata->n_freq) {
            fprintf(stderr,"ERROR: inps %d,%d. expected to read %d channels, only got %d\n",inp1, inp2,uvdata->n_freq,n_read);
            exit(1);
        }
 
         /* throw away cross correlations from different pols on the same antenna if we only want cross products */
         /* we do this here to make sure that the data is read and the file advanced on to data we want */
         if (header->corr_type=='C' && ant1==ant2) continue;
 
        /* calc u,v,w for this baseline in meters */
        u=v=w=0.0;
        if(ant1 != ant2) {
            u = ant_u[ant1] - ant_u[ant2];
            v = ant_v[ant1] - ant_v[ant2];
            w = ant_w[ant1] - ant_w[ant2];
        }

        /* populate the baseline info. Antenna numbers start at 1 in UVFITS.  */
        uvdata->baseline[scan][bl_index] = 0; // default: no baseline. useful to catch bugs.
        EncodeBaseline(ant1+1, ant2+1, uvdata->baseline[scan]+bl_index);
        /* arcane units of UVFITS require u,v,w in nanoseconds */
        uvdata->u[scan][bl_index] = u/VLIGHT;
        uvdata->v[scan][bl_index] = v/VLIGHT;
        uvdata->w[scan][bl_index] = w/VLIGHT;

        if (debug) {
            fprintf(fpd,"doing inps %d,%d. ants: %d,%d pols: %d,%d, polind: %d, bl_ind: %d, w (m): %g, delay (m): %g, blrev: %d\n",
                    inp1,inp2,ant1,ant2,pol1,pol2,pol_ind,bl_index,w,cable_delay,baseline_reverse);
        }
        
        /* if not correcting for geometry, don't apply w */
        if(!header->geom_correct) {
            w = 0.0;
        }

        /* populate the visibility arrays */
        for(chan_ind=0; chan_ind<uvdata->n_freq; chan_ind++) {
            double freq,lambda;
            complex vis,phase=1.0;

            /* calc wavelen for this channel in meters. header freqs are in MHz*/
            freq = (header->cent_freq + (header->invert_freq? -1.0:1.0)*(chan_ind - uvdata->n_freq/2.0)/uvdata->n_freq*header->bandwidth);
            lambda = (VLIGHT/1e6)/freq;
            phase = cexp(I*(-2.0*M_PI)*(w+cable_delay*(baseline_reverse? -1.0:1.0))/lambda);
            visindex = bl_index*uvdata->n_pol*uvdata->n_freq + chan_ind*uvdata->n_pol + pol_ind;
            vis = visdata[chan_ind*2] + I*(header->conjugate ? -visdata[chan_ind*2+1]: visdata[chan_ind*2+1]);

            if(debug && chan_ind==uvdata->n_freq/2) {
                fprintf(fpd,"Chan %d, w: %g (wavelen), vis: %g,%g. ph: %g,%g. rot vis: %g,%g\n",chan_ind,w/lambda,creal(vis),cimag(vis),creal(phase),cimag(phase),creal(vis*phase),cimag(vis*phase));
            }

            if (baseline_reverse) vis = conj(vis);
            vis *= phase;

            if (inp1 != inp2) {
                /* cross correlation, use imaginary and real */
                uvdata->visdata[scan][visindex*2   ] = crealf(vis);
                uvdata->visdata[scan][visindex*2 +1] = cimagf(vis);
            }
            else {
                /* auto correlation, set imag to zero */
                uvdata->visdata[scan][visindex*2   ] = visdata[chan_ind];
                uvdata->visdata[scan][visindex*2 +1] = 0.0;
            }
            uvdata->weightdata[scan][visindex] = vis_weight;
            // apply input-based flags if necessary
            if ( (inps->inpFlag[inp1] || inps->inpFlag[inp2]) && vis_weight > 0) {
                uvdata->weightdata[scan][visindex] = -vis_weight;
            }
        }
    }

  }
  if (visdata != NULL) free(visdata);
  return 0;
}


/***************************************
 examine the ordering of polarisation products from maps and create an
 index to order them the way miriad likes: i.e. XX, YY, XY, YX
 typically they will be XX,XY,YX,YY from MAPS
 **************************************/
int createPolIndex(char *polprods, int *index) {
  int p1='\0',p2='\0',i;

  /* find the unique letters representing the pol products. i.e. X,Y or R,L or II */
  for (i=0; i<strlen(polprods); i++) {
    if (p1=='\0' && polprods[i] != '\0') {
      p1 = polprods[i];
      continue;
    }
    if (p2=='\0' && polprods[i] != '\0' && p1 != polprods[i]) {
      p2 = polprods[i];
      continue;
    }
  }
  if (debug) fprintf(fpd,"Found pol keys '%c' and '%c'\n",p1,p2);

  /* find the index of products */
  for (i=0; i<4; i++) {
    if (polprods[i*2]==p1 && polprods[i*2+1]==p1) index[0] = i;
    if (polprods[i*2]==p2 && polprods[i*2+1]==p2) index[1] = i;
    if (polprods[i*2]==p1 && polprods[i*2+1]==p2) index[2] = i;
    if (polprods[i*2]==p2 && polprods[i*2+1]==p1) index[3] = i;
  }
  if (debug) {
    for (i=0; i<4; i++) fprintf(fpd,"polindex: %d ",index[i]);
    fprintf(fpd,"\n");
  }
  return 0;
}


/******************************
 read the station locations from a text
 file and populate the antenna positions in the
 data structure.
*******************************/
int readArray(char *filename, double lat_radian, ant_table *antennas, int *n_ants) {
  FILE *fp=NULL;
  char line[MAX_LINE];
  int index=0,nscan;
  double east=0,north=0,height=0;

  if( (fp=fopen(filename,"r"))==NULL) {
    fprintf(stderr,"ERROR: readArray: failed to open array file <%s>\n",filename);
    return 1;
  }

  /* scan through lines. convert east,north,height units to XYZ units */
  while((fgets(line,MAX_LINE-1,fp)) !=NULL) {
    if(line[0]=='\n' || line[0]=='#' || line[0]=='\0') continue; // skip blank/comment lines
    nscan = sscanf(line,"%8s %lf %lf %lf",antennas[index].name,&east,&north,&height);
    if(nscan != 4) {
        fprintf(stderr,"Failed scanning antenna file with line: <%s>\n",line);
        return 1;
    }
    ENH2XYZ_local(east,north,height,lat_radian,antennas[index].xyz_pos,antennas[index].xyz_pos+1,antennas[index].xyz_pos+2);
    if (debug) {
      fprintf(fpd,"ant %s. Pos (ENH) (%g,%g,%g).\tPos (XYZ): (%g,%g,%g)\n",antennas[index].name, east,north,height,
          antennas[index].xyz_pos[0],antennas[index].xyz_pos[1],antennas[index].xyz_pos[2]);
    }
    antennas[index].station_num = index;
    index++;
    if (index > MAX_ANT) {
        fprintf(stderr,"ERROR: there are too many antennas. Increase MAX_ANT and recompile.\n");
        exit(1);
    }
  }
  *n_ants = index;
  fclose(fp);
  return 0;
}


/******************************
 read the mapping between antennas and correlator inputs.
*******************************/
int readInputConfig(char *filename, InpConfig *inp) {
  FILE *fp=NULL;
  char line[MAX_LINE],pol_char;
  int index=0,dummy,nscan,i,inp_flag;

  if( (fp=fopen(filename,"r"))==NULL) {
    fprintf(stderr,"ERROR: readInputConfig: failed to open array file <%s>\n",filename);
    return 1;
  }
  
  for (i=0; i<MAX_ANT*2; i++) inp->inpFlag[i] = 0;

  /* scan through lines.  */
  while((fgets(line,MAX_LINE-1,fp)) !=NULL) {
    if(line[0]=='\n' || line[0]=='#' || line[0]=='\0') continue; // skip blank/comment lines

    inp_flag=0;

    nscan = sscanf(line,"%d %d %c %f %d",&dummy,inp->ant_index+index,&pol_char,inp->cable_len_delta+index,&inp_flag);
    if(nscan < 4) {
        fprintf(stderr,"Failed scanning instr config file with line: <%s>\n",line);
        return 1;
    }

    inp->inpFlag[index] = inp_flag;
    
    inp->pol_index[index] = decodePolChar(pol_char);
    if (debug) {
        fprintf(fpd,"input: %d is antenna %d with pol %d. Length delta: %g\n",index,inp->ant_index[index],
                    inp->pol_index[index],inp->cable_len_delta[index]);
    }
    index++;
  }
  inp->n_inputs = index;
  fclose(fp);
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
          case 'S': stationfilename = optarg;
            break;
          case 'o': outfilename = optarg;
            break;
          case 'a': autocorr_filename = optarg;
            break;
          case 'c': crosscor_filename = optarg;
            break;
          case 'd': debug = 1;
            fprintf(fpd,"Debugging on...\n");
            break;
          case 'I': configfilename = optarg;
            break;
          case 'H': header_filename = optarg;
            break;
          case 'f': do_flag=atoi(optarg);
            break;
          case 'F': flagfilename=optarg;
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
        arr_lat_rad = atof(lat);
        arr_lon_rad = atof(lon);
        fprintf(fpd,"User specified array lon,lat: %g, %g (degs)\n",arr_lon_rad,arr_lat_rad);
        arr_lat_rad *= (M_PI/180.0); // convert to radian
        arr_lon_rad *= (M_PI/180.0);
    }

    /* do some sanity checks */
    if(outfilename==NULL) {
        fprintf(stderr,"ERROR: no output file name specified\n");
        exit(1);
    }
    /* auto flagging requires autocorrelations */
    if (autocorr_filename==NULL && do_flag) {
        fprintf(stderr,"ERROR: auto flagging requires the autocorrelations to be used\n");
        exit(1);
    }
}


/***************************
 ***************************/
void printusage(const char *progname) {
  fprintf(stderr,"Usage: %s [options]\n\n",progname);
  fprintf(stderr,"options are:\n");
  fprintf(stderr,"-a filename\tThe name of autocorrelation data file. no default.\n");
  fprintf(stderr,"-c filename\tThe name of cross-correlation data file. no default.\n");
  fprintf(stderr,"-o filename\tThe name of the output file. No default.\n");
  fprintf(stderr,"-S filename\tThe name of the file containing antenna name and local x,y,z. Default: %s\n",stationfilename);
  fprintf(stderr,"-I filename\tThe name of the file containing instrument config. Default: %s\n",configfilename);
  fprintf(stderr,"-H filename\tThe name of the file containing observing metadata. Default: %s\n",header_filename);
  fprintf(stderr,"-A lon,lat \tSpecify East Lon and Lat of array center (degrees). Comma separated, no spaces. Default: MWA 32T\n");
  fprintf(stderr,"-l         \tLock the phase center to the initial HA/DEC\n");
  fprintf(stderr,"-f mode    \tturn on automatic flagging. Requires autocorrelations\n");
  fprintf(stderr,"\t\t0:\tno flagging\n");
  fprintf(stderr,"\t\t1:\tgeneric flagging\n");
  fprintf(stderr,"\t\t2:\tspecial treatment for MWA edge channels, 40kHz case\n");
  fprintf(stderr,"\t\t3:\tspecial treatment for MWA edge channels, 10kHz case\n");
  fprintf(stderr,"-F filename\tOptionally apply global flags as specified in filename.\n");
  fprintf(stderr,"-d         \tturn debugging on.\n");
  fprintf(stderr,"-v         \treturn revision number and exit.\n");
  exit(1);
}


/***************************
 ***************************/
int readHeader(char *header_filename, Header *header) {
    FILE *fp=NULL;
    char line[MAX_LINE],key[MAX_LINE],value[MAX_LINE];
    int nscan;
    
    if((fp=fopen(header_filename,"r"))==NULL) {
        fprintf(stderr,"ERROR: failed to open obs metadata file <%s>\n",header_filename);
        exit(1);
    }
    header->n_scans=0;
    header->n_inputs  = 0;
    header->n_chans=0;
    header->corr_type = 'N';
    header->integration_time = 0.0;
    header->cent_freq = 0;
    header->bandwidth = 0;
    header->ha_hrs_start = -99.0;
    header->ra_hrs = -99.0;
    header->dec_degs = -99.0;
    header->ref_el = M_PI/2.0;
    header->ref_az = 0.0;
    header->year=0;
    header->month=0;
    header->day=0;
    header->ref_hour=0;
    header->ref_minute=0;
    header->ref_second=0;
    header->field_name[0] = '\0';
    header->invert_freq = 0;    // correlators have now been fixed
    header->conjugate = 0;      // just in case.
    header->geom_correct = 1;   // default, stop the fringes
    
    while((fgets(line,MAX_LINE-1,fp)) !=NULL) {
        if(line[0]=='\n' || line[0]=='#' || line[0]=='\0') continue; // skip blank/comment lines

        nscan = sscanf(line,"%s %s",key,value);
        if (strncmp(key,"FIELDNAME",MAX_LINE)==0) strcpy(header->field_name,value);
        if (strncmp(key,"N_SCANS",MAX_LINE)==0) header->n_scans = atoi(value);
        if (strncmp(key,"N_INPUTS",MAX_LINE)==0) header->n_inputs = atoi(value);
        if (strncmp(key,"N_CHANS",MAX_LINE)==0) header->n_chans = atoi(value);
        if (strncmp(key,"CORRTYPE",MAX_LINE)==0) header->corr_type = toupper(value[0]);
        if (strncmp(key,"INT_TIME",MAX_LINE)==0) header->integration_time = atof(value);
        if (strncmp(key,"FREQCENT",MAX_LINE)==0) header->cent_freq = atof(value);
        if (strncmp(key,"BANDWIDTH",MAX_LINE)==0) header->bandwidth = atof(value);
        if (strncmp(key,"INVERT_FREQ",MAX_LINE)==0) header->invert_freq = atoi(value);
        if (strncmp(key,"CONJUGATE",MAX_LINE)==0) header->conjugate = atoi(value);
        if (strncmp(key,"GEOM_CORRECT",MAX_LINE)==0) header->geom_correct = atoi(value);
        if (strncmp(key,"REF_AZ",MAX_LINE)==0) header->ref_az = atof(value)*(M_PI/180.0);
        if (strncmp(key,"REF_EL",MAX_LINE)==0) header->ref_el = atof(value)*(M_PI/180.0);
        if (strncmp(key,"HA_HRS",MAX_LINE)==0) header->ha_hrs_start = atof(value);
        if (strncmp(key,"RA_HRS",MAX_LINE)==0) header->ra_hrs = atof(value);
        if (strncmp(key,"DEC_DEGS",MAX_LINE)==0) header->dec_degs = atof(value);
        if (strncmp(key,"DATE",MAX_LINE)==0) {
            header->day = atoi(value+6); value[6]='\0';
            header->month = atoi(value+4); value[4]='\0';
            header->year = atoi(value);
        }
        if (strncmp(key,"TIME",MAX_LINE)==0) {
            header->ref_second = atof(value+4); value[4]='\0';
            header->ref_minute = atoi(value+2); value[2]='\0';
            header->ref_hour = atoi(value);
            if (debug) fprintf(fpd,"Time: %d:%d:%f\n",header->ref_hour,header->ref_minute,header->ref_second);
        }
    
    }

    /* sanity checks and defaults */
    strcpy(header->pol_products,"XXXYYXYY");
    if (header->n_scans==0) {
        header->n_scans=1;
        fprintf(stderr,"WARNING: N_SCANS unspecified. Assuming: %d\n",header->n_scans);
    }
    if(header->field_name[0] == '\0') strcpy(header->field_name,"TEST_32T");
    if (header->n_inputs==0) {
        header->n_inputs=16;
        fprintf(stderr,"WARNING: N_INPUTS unspecified. Assuming: %d\n",header->n_inputs);
    }
    if (header->n_chans==0) {
        header->n_chans=128;
        fprintf(stderr,"WARNING: N_CHANS unspecified. Assuming: %d\n",header->n_chans);
    }
    if (header->corr_type=='N') {
        header->corr_type='B';
        fprintf(stderr,"WARNING: CORRTYPE unspecified. Assuming: %c\n",header->corr_type);
    }
    if (header->integration_time==0) {
        header->integration_time=10.0;
        fprintf(stderr,"WARNING: INT_TIME unspecified. Assuming: %g seconds\n",header->integration_time);
    }
    if (header->bandwidth==0) {
        header->bandwidth=1.28;
        fprintf(stderr,"WARNING: BANDWIDTH unspecified. Assuming: %g MHz\n",header->bandwidth);
    }
    if (header->cent_freq==0) {
        fprintf(stderr,"ERROR: FREQCENT unspecified. There is no default.\n");
        return 1;
    }
    if (header->ra_hrs==-99) {
        fprintf(stderr,"ERROR: RA_HRS unspecified. There is no default.\n");
        return 1;
    }
    if (header->dec_degs==-99) {
        fprintf(stderr,"ERROR: DEC_DEGS unspecified. There is no default.\n");
        return 1;
    }
    if (header->year==0 || header->month==0 || header->day==0) {
        fprintf(stderr,"ERROR: DATE unspecified. There is no default.\n");
        return 1;
    }
    if (header->ha_hrs_start == -99.0 && lock_pointing) {
        fprintf(stderr,"ERROR: HA must be specified in header if -l flag is used.\n");
        return 1;
    }
    //header->ref_hour=0;
    //header->ref_minute=0;
    //header->ref_second=0;

    if(fp!=NULL) fclose(fp);
    return 0;
}


/*******************************
*********************************/
void initData(uvdata *data) {
  data->date = calloc(1,sizeof(double));
  data->n_pol=0;
  data->n_baselines=NULL;
  data->n_freq=0;
  data->n_vis=0;
  data->cent_freq=0.0;
  data->freq_delta = 0.0;
  data->u=NULL;
  data->v=NULL;
  data->w=NULL;
  data->baseline=NULL;
  data->weightdata=NULL;
  data->visdata=NULL;
  data->pol_type=1;    /* default is Stokes pol products */
  data->array->n_ant=0;
  strcpy(data->array->name,"MWA-32T");
}


/***********************
***********************/
int applyHeader(Header *header, uvdata *data) {

  double jdtime_base=0;
  int n_polprod=0,i,res;

  data->n_freq = header->n_chans;
  data->cent_freq = header->cent_freq*1e6;
  data->freq_delta = header->bandwidth/(header->n_chans)*1e6*(header->invert_freq ? -1.0: 1.0);

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

  strncpy(data->source->name,header->field_name,SIZE_SOURCE_NAME-1);

  /* extract RA, DEC from header. Beware negative dec and negative zero bugs. */
  data->source->ra  = header->ra_hrs;
  data->source->dec = header->dec_degs;

  return 0;
}


/**************************
**************************/
void calcUVW(double ha,double dec,double x,double y,double z,double *u,double *v,double *w) {
    double sh,ch,sd,cd;

    sh = sin(ha); sd = sin(dec);
    ch = cos(ha); cd = cos(dec);
    *u  = sh*x + ch*y;
    *v  = -sd*ch*x + sd*sh*y + cd*z;
    *w  = cd*ch*x  - cd*sh*y + sd*z;
}


/**************************
***************************/
void checkInputs(Header *header,uvdata *data,InpConfig *inputs) {
    int total_ants;

    if(inputs->n_inputs != header->n_inputs) {
        fprintf(stderr,"ERROR: mismatch between the number of inputs in %s (%d) and header (%d)\n",
                configfilename,inputs->n_inputs,header->n_inputs);
        exit(1);
    }

    total_ants = countPresentAntennas(inputs);

    if (total_ants > data->array->n_ant) {
        fprintf(stderr,"ERROR: mismatch between the number of antennas in %s (%d) and %s (%d)\n",
                stationfilename,data->array->n_ant,configfilename,total_ants);
    }
    
    if (do_flag && header->corr_type == 'C') {
        fprintf(stderr,"ERROR: CORRTYPE must be auto or both for autoflagging\n");
        exit(1);
    }
}


/**************************
***************************/
int decodePolChar(int pol_char) {
    int temp;
    temp = toupper(pol_char);
    if (temp == 'X' || temp == 'R'|| temp=='I') return 0;
    if (temp == 'Y' || temp == 'L') return 1;
    fprintf(stderr,"WARNING: Unknown pol char: <%c>\n",pol_char);
    return 0;
}


/**************************
***************************/
int decodePolIndex(int pol1, int pol2) {

    if (pol1==0 && pol2==0) return 0;
    if (pol1==1 && pol2==1) return 1;
    if (pol1==0 && pol2==1) return 2;
    if (pol1==1 && pol2==0) return 3;
    return 0;
}



/**************************
***************************/
void azel2xyz(double az, double el, double *x, double *y, double *z) {
    double sa,ca,se,ce;
    
    sa = sin(az); se = sin(el);
    ca = cos(az); ce = cos(el);

    *x = sa*ce;
    *y = ca*ce;
    *z = se;
}


/*************************
 count the number of antennas actuall present in this data.
 might be less than the number of antennas in the array configuration 
**************************/
int countPresentAntennas(InpConfig *inputs) {
    int i,ant_present[MAX_ANT],total_ants=0;

    memset(ant_present,'\0',sizeof(int)*MAX_ANT);
    
    for(i=0; i<inputs->n_inputs; i++) ant_present[inputs->ant_index[i]] =1;
    for(i=0; i<MAX_ANT; i++) total_ants += ant_present[i];

    return total_ants;

}

/***********************
 check if an antenna is being used in the current config\
 returns 1 (true) or 0 (false)
 ***********************/
int checkAntennaPresent(InpConfig *inputs, int ant_index) {
    int i;

    for (i=0; i<inputs->n_inputs; i++) {
        if (inputs->ant_index[i] == ant_index) return 1;
    }

    return 0;
}

/**************************
***************************/
/* lmst, lmst2000 are the local mean sidereal times in radians
 * for the obs. and J2000 epochs.
 */
void precXYZ(double rmat[3][3], double x, double y, double z, double lmst,
         double *xp, double *yp, double *zp, double lmst2000)
{
  double sep, cep, s2000, c2000;
  double xpr, ypr, zpr, xpr2, ypr2, zpr2;

  sep = sin(lmst);
  cep = cos(lmst);
  s2000 = sin(lmst2000);
  c2000 = cos(lmst2000);

  /* rotate to frame with x axis at zero RA */
  xpr = cep*x - sep*y;
  ypr = sep*x + cep*y;
  zpr = z;

  xpr2 = (rmat[0][0])*xpr + (rmat[0][1])*ypr + (rmat[0][2])*zpr;
  ypr2 = (rmat[1][0])*xpr + (rmat[1][1])*ypr + (rmat[1][2])*zpr;
  zpr2 = (rmat[2][0])*xpr + (rmat[2][1])*ypr + (rmat[2][2])*zpr;

  /* rotate back to frame with xp pointing out at lmst2000 */
  *xp = c2000*xpr2 + s2000*ypr2;
  *yp = -s2000*xpr2 + c2000*ypr2;
  *zp = zpr2;
}

/**************************
***************************/
/* rmat = 3x3 rotation matrix for going from one to another epoch
 * ra1, dec1, ra2, dec2 are in radians
 */

void rotate_radec(double rmat[3][3], double ra1, double dec1,
          double *ra2, double *dec2)
{
   double v1[3], v2[3];

  slaDcs2c(ra1,dec1,v1);
  slaDmxv(rmat,v1,v2);
  slaDcc2s(v2,ra2,dec2);
  *ra2 = slaDranrm(*ra2);
}

/**************************
***************************/
/* ra, dec are in radians in this function call
 */

void aber_radec_rad(double eq, double mjd, double ra1, double dec1, double *ra2, double *dec2)
{
  double v1[3], v2[3];

  slaDcs2c(ra1,dec1,v1);
  stelaber(eq,mjd,v1,v2);
  slaDcc2s(v2,ra2,dec2);
  *ra2 = slaDranrm(*ra2);
}

/**************************
***************************/
/* eq = epoch of equinox to be used (e.g., 2000.0 for J2000)
 * mjd = Modified Julian Date (TDB) of correction
 *  will ignore MJD(UTC) vs. MJD(TDB) difference here
 * v1[3] = vector in barycenter frame
 * v2[3] = corresponding vector in Earth-centered frame
 *       = apparent direction from Earth
 */

void stelaber(double eq, double mjd, double v1[3], double v2[3])
{
   double amprms[21], v1n[3], v2un[3], w, ab1, abv[3], p1dv;
   int i;

   slaMappa(eq,mjd,amprms);


/* code from mapqk.c (w/ a few names changed): */

/* Unpack scalar and vector parameters */
   ab1 = amprms[11];
   for ( i = 0; i < 3; i++ )
   {
      abv[i] = amprms[i+8];
   }

   slaDvn ( v1, v1n, &w );

/* Aberration (normalization omitted) */
   p1dv = slaDvdv ( v1n, abv );
   w = 1.0 + p1dv / ( ab1 + 1.0 );
   for ( i = 0; i < 3; i++ ) {
      v2un[i] = ab1 * v1n[i] + w * abv[i];
   }

/* normalize  (not in mapqk.c */
   slaDvn ( v2un, v2, &w );

}

/**************************
***************************/
void mat_transpose(double rmat1[3][3], double rmat2[3][3])
{
  int i, j;

  for(i=0;i<3;++i) {
    for(j=0;j<3;++j) {
      rmat2[j][i] = rmat1[i][j];
    }
  }

}

/**************************
***************************/
/* find components of epoch unit vectors in j2000 frame */

void unitvecs_j2000(double rmat[3][3], double xhat[3], double yhat[3], double zhat[3])

{
  int i;

  for(i=0;i<3;++i) {
    xhat[i] = rmat[i][0];
    yhat[i] = rmat[i][1];
    zhat[i] = rmat[i][2];
  }
}


/**************************
***************************/
/* ra, dec, lmst units = radians */

void ha_dec_j2000(double rmat[3][3], double lmst, double lat_rad, double ra2000,
                  double dec2000, double *newha, double *newlat, double *newlmst)
{
  double nwlmst, nwlat;

  rotate_radec(rmat,lmst,lat_rad,&nwlmst,&nwlat);
  *newlmst = nwlmst;
  *newha = slaDranrm(nwlmst - ra2000);
  *newlat = nwlat;
}

