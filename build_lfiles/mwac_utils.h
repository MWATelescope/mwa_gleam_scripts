/*
 * mwac_utils.h
 *
 *  Created on: Jun 13, 2012
 *      Author: sord
 */

#ifndef MWAC_UTILS_H_
#define MWAC_UTILS_H_



#include <complex.h>
#include <stdlib.h>

#ifdef __cplusplus
extern "C" {
#endif

void fill_mapping_matrix();

void get_baseline( int st1, int st2,int pol1, int pol2, complex float * data,
		complex float * baseline);

void get_baseline_lu( int st1, int st2,int pol1, int pol2, float complex * data,
		float complex * baseline);


void get_baseline_r(int st1, int st2, int pol1, int pol2, float complex * data,
		float complex * baseline, int npol,int nstation, int nfrequency,int true_st1,int true_st2,int true_pol1,int true_pol2,int conjugate);

void extractMatrix(float complex *matrix, float complex * packed);
void extractMatrix_slow(float complex *matrix, float complex * packed);
void full_reorder(float complex *full_matrix_h, float complex *reordered);

#ifdef __cplusplus
}
#endif

#endif /* MWAC_UTILS_H_ */
