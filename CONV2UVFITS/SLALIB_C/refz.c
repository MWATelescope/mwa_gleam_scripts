#include "slalib.h"
#include "slamac.h"
void slaRefz ( double zu, double refa, double refb, double *zr )
/*
**  - - - - - - - -
**   s l a R e f z
**  - - - - - - - -
**
**  Adjust an unrefracted zenith distance to include the effect of
**  atmospheric refraction, using the simple A tan z + B tan^3 z
**  model.
**
**  Given:
**    zu    double    unrefracted zenith distance of the source (radian)
**    refa  double    A: tan z coefficient (radian)
**    refb  double    B: tan^3 z coefficient (radian)
**
**  Returned:
**    *zr   double    refracted zenith distance (radian)
**
**  Notes:
**
**  1  This routine applies the adjustment for refraction in the
**     opposite sense to the usual one - it takes an unrefracted
**     (in vacuo) position and produces an observed (refracted)
**     position, whereas the A tan Z + B tan^3 Z model strictly
**     applies to the case where an observed position is to have the
**     refraction removed.  The unrefracted to refracted case is
**     harder, and requires an inverted form of the text-book
**     refraction models;  the formula used here is based on the
**     Newton-Raphson method.  For the utmost numerical consistency
**     with the refracted to unrefracted model, two iterations are
**     carried out, achieving agreement at the 1D-11 arcseconds level
**     for a ZD of 80 degrees.  The inherent accuracy of the model
**     is, of course, far worse than this - see the documentation for
**     slaRefco for more information.
**
**  2  At ZD 83 degrees, the rapidly-worsening A tan Z + B tan^3 Z
**     model is abandoned and an empirical formula takes over.  For
**     optical/IR wavelengths, over a wide range of observer heights and
**     corresponding temperatures and pressures, the following levels of
**     accuracy (arcsec, worst case) are achieved, relative to numerical
**     integration through a model atmosphere:
**
**              zr    error
**
**              80      0.7
**              81      1.3
**              82      2.4
**              83      4.7
**              84      6.2
**              85      6.4
**              86      8
**              87     10
**              88     15
**              89     30
**              90     60
**              91    150         } relevant only to
**              92    400         } high-elevation sites
**
**     For radio wavelengths the errors are typically 50% larger than
**     the optical figures and by ZD 85 deg are twice as bad, worsening
**     rapidly below that.  To maintain 1 arcsec accuracy down to ZD=85
**     at the Green Bank site, Condon (2004) has suggested amplifying
**     the amount of refraction predicted by slaRefz below 10.8 deg
**     elevation by the factor (1+0.00195*(10.8-E_t)), where E_t is the
**     unrefracted elevation in degrees.
**
**     The high-ZD model is scaled to match the normal model at the
**     transition point;  there is no glitch.
**
**  3  Beyond 93 deg zenith distance, the refraction is held at its
**     93 deg value.
**
**  4  See also the routine slaRefv, which performs the adjustment in
**     Cartesian Az/El coordinates, and with the emphasis on speed
**     rather than numerical accuracy.
**
**  Defined in slamac.h:  DR2D
**
**  Reference:
**
**     Condon,J.J., Refraction Corrections for the GBT, PTCS/PN/35.2,
**     NRAO Green Bank, 2004.
**
**  Last revision:   9 April 2004
**
**  Copyright P.T.Wallace.  All rights reserved.
*/
{
   double zu1, zl, s, c, t, tsq, tcu, ref, e, e2;

/* Coefficients for high ZD model (used beyond ZD 83 deg) */
   const double c1 =  0.55445,
                c2 = -0.01133,
                c3 =  0.00202,
                c4 =  0.28385,
                c5 =  0.02390;

/* Largest usable ZD (deg) */
   const double z93 = 93.0;

/* ZD at which one model hands over to the other (radians) */
   const double z83 = 83.0 / DR2D;

/* High-ZD-model prediction (deg) for that point */
   const double ref83 = ( c1 + c2 * 7.0 + c3 * 49.0 ) /
                       ( 1.0 + c4 * 7.0 + c5 * 49.0 );


/* Perform calculations for zu or 83 deg, whichever is smaller */
   zu1 = gmin ( zu, z83 );

/* Functions of ZD */
   zl = zu1;
   s = sin ( zl );
   c = cos ( zl );
   t = s / c;
   tsq = t * t;
   tcu = t * tsq;

/* Refracted ZD (mathematically to better than 1mas at 70 deg) */
   zl -= ( refa * t + refb * tcu )
            / ( 1.0 + ( refa + 3.0 * refb * tsq ) / ( c * c ) );

/* Further iteration */
   s = sin ( zl );
   c = cos ( zl );
   t = s / c;
   tsq = t * t;
   tcu = t * tsq;
   ref = zu1 - zl + ( zl - zu1 + refa * t + refb * tcu )
             / ( 1.0 + ( refa + 3.0 * refb * tsq ) / ( c * c ) );

/* Special handling for large zu */
   if ( zu > zu1 ) {
      e = 90.0 - gmin ( z93, zu * DR2D );
      e2 = e * e;
      ref = ( ref / ref83 ) * ( c1 + c2 * e + c3 * e2 ) /
                             ( 1.0 + c4 * e + c5 * e2 );
   }

/* Refracted ZD */
   *zr = zu - ref;
}
