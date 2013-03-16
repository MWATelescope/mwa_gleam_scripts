# Makefile for corr2uvfits.

CFLAGS=-g -O -Wall -D_FILE_OFFSET_BITS=64 -L.
CFITSIO_INCS=$(shell pkg-config --silence-errors --cflags cfitsio)
CFITSIO_LIBS=$(shell pkg-config --silence-errors --libs cfitsio)
INCS=$(shell python -c "if len('${INCLUDE}')>0:print ' '.join(['-I ' + s for s in '${INCLUDE}'.split(':')])")

TARGETS=corr2uvfits
SRCDIR=CONV2UVFITS


all: $(TARGETS)

corr2uvfits: corr2uvfits.c uvfits.c libsla.a
	ranlib libsla.a
	cc $(CFLAGS) $(INCS) $(CFITSIO_INCS) -o corr2uvfits corr2uvfits.c uvfits.c $(CFITSIO_LIBS) -lsla -lm

mwacalc: mwacalc.c mwacalc.h CALC_xdr.c CALCServer.h
	cc $(CFLAGS) mwacalc.c CALC_xdr.c -o $@

test_uvw: test_uvw.c libsla.a
	cc $(CFLAGS) test_uvw.c -o $@ -lsla -lm

libsla.a:
	cd SLALIB_C ; make
	rm -f SLALIB_C/*.o
clean:
	rm -f *.o $(TARGETS) libsla.a SLALIB_C/*.o 
	rm -rf corr2uvfits.dSYM
