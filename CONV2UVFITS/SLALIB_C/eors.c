#include "slalib.h"
#include "slamac.h"
double slaEors ( double rnpb[3][3], double s )
/*
**  - - - - - - - -
**   s l a E o r s
**  - - - - - - - -
**
**  Equation of the origins, given the classical NPB matrix and the
**  quantity s.
**
**  Given:
**     rnpb   double[3][3]  classical NPB matrix
**     s      double        the quantity s (the CIO locator)
**
**  Returned:
**            double        the equation of the origins (radians)
**
**  Notes:
**
**  1)  The equation of the origins is the distance between the true
**      equinox and the celestial intermediate origin and, equivalently,
**      the difference between Earth rotation angle and Greenwich
**      apparent sidereal time (ERA-GST).  It comprises the precession
**      (since J2000.0) in right ascension plus the equation of the
**      equinoxes (including the small correction terms).
**
**  2)  The algorithm is from Wallace & Capitaine (2006).
**
**  Reference:
**
**     Wallace, P.T. & Capitaine, N. 2006, A&A (submitted).
**
**  Last revision:   29 July 2006
**
**  Copyright P.T.Wallace.  All rights reserved.
*/
{
   double x, ax, xs, ys, zs, p, q;


/* Evaluate Capitaine & Wallace (2006) expression (16). */
   x = rnpb[2][0];
   ax = x / ( 1.0 + rnpb[2][2] );
   xs = 1.0 - ax * x;
   ys = - ax * rnpb[2][1];
   zs = - x;
   p = rnpb[0][0] * xs + rnpb[0][1] * ys + rnpb[0][2] * zs;
   q = rnpb[1][0] * xs + rnpb[1][1] * ys + rnpb[1][2] * zs;
   return s - ( ( p != 0.0 || q != 0.0 ) ? atan2 ( q, p ) : 0.0 );

}
