#include "slalib.h"
#include "slamac.h"
void slaNut ( double date, double rmatn[3][3] )
/*
**  - - - - - - -
**   s l a N u t
**  - - - - - - -
**
**  Form the matrix of nutation for a given date - Shirai & Fukushima
**  2001 theory
**
**  (double precision)
**
**  Reference:
**     Shirai, T. & Fukushima, T., Astron.J. 121, 3270-3283 (2001).
**
**  Given:
**     date   double        TDB (loosely ET) as Modified Julian Date
**                                           (=JD-2400000.5)
**
**  Returned:
**     rmatn  double[3][3]  nutation matrix
**
**  Notes:
**
**  1  The matrix is in the sense  v(true) = rmatn * v(mean) .
**     where v(true) is the star vector relative to the true equator and
**     equinox of date and v(mean) is the star vector relative to the
**     mean equator and equinox of date.
**
**  2  The matrix represents forced nutation (but not free core
**     nutation) plus corrections to the IAU~1976 precession model.
**
**  3  Earth attitude predictions made by combining the present nutation
**     matrix with IAU~1976 precession are accurate to 1~mas (with
**     respect to the ICRS) for a few decades around 2000.
**
**  4  The distinction between the required TDB and TT is always
**     negligible.  Moreover, for all but the most critical applications
**     UTC is adequate.
**
**  Called:   slaNutc, slaDeuler
**
**  Last revision:   1 December 2005
**
**  Copyright P.T.Wallace.  All rights reserved.
*/
{
   double dpsi, deps, eps0;

/* Nutation components and mean obliquity */
   slaNutc ( date, &dpsi, &deps, &eps0 );

/* Rotation matrix */
   slaDeuler ( "xzx", eps0, -dpsi, - ( eps0 + deps ), rmatn );
}
