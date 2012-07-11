#include "slalib.h"
#include "slamac.h"
void slaPrenut ( double epoch, double date, double rmatpn[3][3] )
/*
**  - - - - - - - - - -
**   s l a P r e n u t
**  - - - - - - - - - -
**
**  Form the matrix of precession and nutation (SF2001)
**
**  (double precision)
**
**  Given:
**     epoch   double         Julian epoch for mean coordinates
**     date    double         Modified Julian Date (JD-2400000.5)
**                            for true coordinates
**
**
**  Returned:
**     rmatpn  double[3][3]   combined precession/nutation matrix
**
**  Called:  slaPrec, slaEpj, slaNut, slaDmxm
**
**  Notes:
**
**  1)  The epoch and date are TDB (loosely ET).  TT (or even UTC) will
**      do.
**
**  2)  The matrix is in the sense   v(true)  =  rmatpn * v(mean) .
**
**  Last revision:   3 December 2005
**
**  Copyright P.T.Wallace.  All rights reserved.
*/
{
   double rmatp[3][3], rmatn[3][3];

/* Precession */
   slaPrec ( epoch, slaEpj ( date ), rmatp );

/* Nutation */
   slaNut ( date, rmatn );

/* Combine the matrices:  pn = n x p */
   slaDmxm ( rmatn, rmatp, rmatpn );
}
