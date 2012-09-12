# Makefile for corr2uvfits.
INCS=$(shell python -c "if len('${INCLUDE}')>0:print ' '.join(['-I ' + s for s in '${INCLUDE}'.split(':')])") -L${CFITSLIB} -I${CFITSINC}
CFLAGS=-g -O -Wall $(INCS) -D_FILE_OFFSET_BITS=64 -L.

TARGETS=corr2uvfits
SRCDIR=CONV2UVFITS


all: $(TARGETS)

corr2uvfits: corr2uvfits.c uvfits.c libsla.a
	cc $(CFLAGS) -o corr2uvfits corr2uvfits.c uvfits.c -lcfitsio -lsla -lm

libsla.a:
	cd SLALIB_C ; make
	rm -f SLALIB_C/*.o
clean:
	rm -f *.o $(TARGETS) libsla.a SLALIB_C/*.o 
	rm -rf corr2uvfits.dSYM
