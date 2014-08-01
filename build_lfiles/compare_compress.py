#!/usr/bin/python
"""A tool for comparing raw MWA data before and after compression.
Randall Wayth. May 2014.
"""

import sys,pyfits,numpy

def compare_compress(uncomp_filename, compressed_filename):
    """
    Compare uncompressed and compressed data and make a report of maximum abs
    and relative difference.
    """

    hdulist_u = pyfits.open(uncomp_filename)
    hdulist_c = pyfits.open(compressed_filename)

    # first sanity check: number of HDUs
    assert len(hdulist_u) == len(hdulist_c), "Mismatch in number of HDUs"

    maxdiffs=[]
    reldiffs=[]

    # loop through each HDU. Compare data and collect stats on max abs and relative difference
    for i in range(len(hdulist_u)):
        d_c = hdulist_c[i].data
        d_u = hdulist_u[i].data
        if d_u is None: continue

        assert d_u.shape == d_c.shape, "Mismatch in shape at HDU index $d" % (i)

        diff = numpy.abs(d_u - d_c).flatten()
        reldiffnonzeroind = numpy.flatnonzero(numpy.fabs(d_u) > 1e-1)
        reldiff = diff[reldiffnonzeroind] / numpy.abs(d_u.flatten()[reldiffnonzeroind])
        p = numpy.argmax(diff)
        prel = numpy.argmax(reldiff)
        maxdiffs.append(diff[p])
        reldiffs.append(reldiff[prel])
        print "HDU %d. Max diff: %f. Rel diff at max: %g" % (i,maxdiffs[-1],reldiffs[-1])

    # report:
    print "Largest abs diff: "+str(numpy.max(maxdiffs))
    print "Largest rel diff: "+str(numpy.max(reldiffs))

def usage():
    print >> sys.stderr, "Usage:"
    print >> sys.stderr, "%s uncompressed_filename compressed_filename" % (sys.argv[0])
    sys.exit(0)

# execute a series of tests if invoked from the command line
if __name__ == "__main__":

    if len(sys.argv) < 3: usage()
    compare_compress(sys.argv[1],sys.argv[2])

