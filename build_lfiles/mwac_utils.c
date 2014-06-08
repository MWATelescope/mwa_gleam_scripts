#include <stdlib.h>
#include <stdio.h>
#include <omp.h>
//#include <plot.h>
#include "mwac_utils.h"
#include "antenna_mapping.h"


void fill_mapping_matrix() {

	extern map_t corr_mapping[NINPUT][NINPUT];
	extern int pfb_output_to_input[NINPUT];
	extern int single_pfb_mapping[64];
	extern int npol;
	extern int nstation;

	int inp1 = 0, inp2 = 0;
	int pol1 = 0, pol2 = 0;
	int index1 = 0, index2 = 0;
	int p=0,npfb = 4;
	
	//	 Output matrix has ordering
	//	 [channel][station][station][polarization][polarization][complexity]

	for (p=0;p<npfb;p++) {
		for (inp1=0;inp1<64;inp1++) {
			pfb_output_to_input[(p*64) + inp1] = single_pfb_mapping[inp1] + (p*64);
		}
	}

			 
	for (inp1 = 0; inp1 < nstation; inp1++) {
		for (inp2 = 0; inp2 < nstation; inp2++) {
			for (pol1 = 0; pol1 < npol; pol1++) {
				for (pol2 = 0; pol2 < npol; pol2++) {
					index1 = inp1 * npol + pol1;
					index2 = inp2 * npol + pol2;
					/*
					   fprintf(stdout,
					   "inp1 %d pol1 %d inp2 %d pol2 %d map to index1 %d and index2 %d\n",
					   inp1, pol1, inp2, pol2, index1, index2);
					   fprintf(stdout,
					   "these map to PFB input numbers: %d and %d\n",
					   pfb_output_to_input[index1],
					   pfb_output_to_input[index2]);
					   */
					corr_mapping[pfb_output_to_input[index1]][pfb_output_to_input[index2]].stn1 =
						inp1; // this should give us the pfb input
					corr_mapping[pfb_output_to_input[index1]][pfb_output_to_input[index2]].stn2 =
						inp2;
					corr_mapping[pfb_output_to_input[index1]][pfb_output_to_input[index2]].pol1 =
						pol1;
					corr_mapping[pfb_output_to_input[index1]][pfb_output_to_input[index2]].pol2 =
						pol2;

				}
			}
		}
	}

}

void get_baseline(int st1, int st2, int pol1, int pol2, float complex *data,
		float complex *baseline) {

	int i, j, k, l, m;
	float complex *in, *out;
	extern int npol;
	extern int nstation;
	extern int nfrequency;
	in = data;
	out = baseline;

	for (i = 0; i < nfrequency; i++) {
		for (j = 0; j < nstation; j++) {
			for (k = 0; k < nstation; k++) {
				for (l = 0; l < npol; l++) {
					for (m = 0; m < npol; m++) {
						if (j == st1 && k == st2) {
							if (l == pol1 && m == pol2) {

								*out = *in;
								out++;
								// fprintf(stdout,"%f %f\n",crealf(*in),cimagf(*in));
							}

						}
						in++;
					}

				}
			}
		}
	}
}


void get_baseline_lu(int st1, int st2, int pol1, int pol2, float complex *data,
		float complex *baseline) {

    int i=0;
    float complex *in, *out;	
        
    extern int npol;
    extern int nstation;
    extern int nfrequency;

    off_t in_index=0,offset,stride;

    in = data;
    out = baseline;

	/* direct lookup */
//    offset = (st1*nstation*npol*npol) + (st2*npol*npol) + (pol1*npol) + pol2;
    offset = npol*((st1*nstation*npol) + (st2*npol) + pol1) + pol2;
    stride = (nstation*nstation*npol*npol);
    for (i=0;i<nfrequency;i++) {
        in_index = i*stride + offset;
        out[i] = in[in_index];
    }
}

void get_baseline_r(int st1, int st2, int pol1, int pol2, float complex *data,
		float complex *reorder,int npol, int nstation, int nfrequency,int true_st1,int true_st2,
		int true_pol1,int true_pol2,int conjugate) {

	int i=0;
	float complex *in, *out;
	size_t out_index =0, in_index=0;;
	in = data;
	out = reorder;
	
/* direct lookup */

	for (i=0;i<nfrequency;i++) {

		in_index = i*(nstation*nstation*npol*npol) + (st1*nstation*npol*npol) + (st2*npol*npol) + (pol1*npol) + pol2;
		out_index = i*(nstation*(nstation+1)*npol*npol/2) + (((true_st1*nstation) - ((true_st1+1)/2)*true_st1) + true_st2)*npol*npol + (pol1*npol) + pol2;
		if (!conjugate) {
			out[out_index] = in[in_index];
		}
		else {
			if (st2>st1) {
				out[out_index] = conj(in[in_index]);
			}
		}
	}

}
// full reorder using the correct mapping - takes the input cube and produces a packed triangular output
// in the correct order

// wacky packed tile order to packed triangular

void full_reorder(float complex *full_matrix_h, float complex *reordered)
{


	extern int npol;
	extern int nstation;
	extern int nfrequency;
	extern map_t corr_mapping[NINPUT][NINPUT];
	
	int t1=0;
	int t2=0;
	int p1=0;
	int p2=0;

	long long baseline_count = 0;

	for (t1 = 0; t1 < nstation; t1++) {
		for (t2 = t1; t2 < nstation; t2++) {
			for (p1 = 0;p1 < npol;p1++) {
				for (p2 =0; p2 < npol; p2++) {
					baseline_count++;

					int index1 = t1 * npol + p1;
					int index2 = t2 * npol + p2;
					/*
					   fprintf(stdout, "requesting ant1 %d ant 2 %d pol1 %d pol2 %d",
					   antenna1, antenna2, pol1, pol2);
					 */
					map_t the_mapping = corr_mapping[index1][index2];
					int conjugate = 0;
					/*
					   fprintf(stdout,
					   "input ant/pol combination decodes to stn1 %d stn2 %d pol1 %d pol2 %d\n",
					   the_mapping.stn1, the_mapping.stn2, the_mapping.pol1,
					   the_mapping.pol2);
					 */


					if (the_mapping.stn2 > the_mapping.stn1) {
						conjugate = 1;
					}
					else {
						conjugate = 0;
					}

					get_baseline_r(the_mapping.stn1, the_mapping.stn2, the_mapping.pol1,
							the_mapping.pol2, full_matrix_h, reordered,npol,nstation,nfrequency,conjugate,t1,t2,p1,p2);

				}
			}
		}
	}

	// now reoredered should contain a triagular packed array in the correct order
}
// Extracts the full matrix from the packed Hermitian form
void extractMatrix(float complex *matrix, float complex *packed) {
	int f;

	extern int npol;
	extern int nstation;
	extern int nfrequency;

    /* use openmp to parallelise this. In single threaded version, this task takes 1/3 the overall CPU time,
        so 4 threads should be plenty to make this negligible
    */
    omp_set_num_threads(4);
    #pragma omp parallel private (f)
    {
    #pragma omp for
	for (f = 0; f < nfrequency; f++) {
        int i,j,pol1,pol2;
		for (i = 0; i < nstation; i++) {
			for (j = 0; j <= i; j++) {
				int k = f * (nstation + 1) * (nstation / 2) + i * (i + 1) / 2 + j;
				for (pol1 = 0; pol1 < npol; pol1++) {
					for (pol2 = 0; pol2 < npol; pol2++) {
						int index = (k * npol + pol1) * npol + pol2;
						matrix[(((f * nstation + i) * nstation + j) * npol + pol1) * npol + pol2] = packed[index];
						matrix[(((f * nstation + j) * nstation + i) * npol + pol2) * npol + pol1] = conjf(packed[index]);
					//	printf("f:%d s1:%d s2:%d %d p1:%d p2:%d %d\n",f,i,j,k,pol1,pol2,index);
					}
				}
			}
		}
	}
    }   // end openmp
}
void extractMatrix_slow(float complex *matrix, float complex *packed) {
	int f, i, j, pol1, pol2;

	extern int npol;
	extern int nstation;
	extern int nfrequency;
	int in_index=0;
	int out_index=0;
	int out_index_conj=0;

	for (f = 0; f < nfrequency; f++) {
		for (i = 0; i < nstation; i++) {
			for (j = 0; j <= i; j++) {
				for (pol1 = 0; pol1 < npol; pol1++) {
					for (pol2 = 0; pol2 < npol; pol2++) {

						out_index = f*(nstation*nstation*npol*npol) + i*(nstation*npol*npol) + j*(npol*npol) + pol1*(npol) + pol2;
						out_index_conj = f*(nstation*nstation*npol*npol) + j*(nstation*npol*npol) + i*(npol*npol) + pol1*(npol) + pol2;
 						matrix[out_index] = packed[in_index];
						matrix[out_index_conj] = conjf(packed[in_index]);
						in_index++;
					}
				}
			}
		}
	}

}
