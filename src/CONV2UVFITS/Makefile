# Makefile for corr2uvfits.
INCS=-I$(SIM_INC) -I/usr/include/cfitsio
CFLAGS=-g -O -Wall $(INCS) -D_FILE_OFFSET_BITS=64 -L.

TARGETS=corr2uvfits mwacalc

all: $(TARGETS)

corr2uvfits: corr2uvfits.c uvfits.c libsla.a
	cc $(CFLAGS) -o corr2uvfits corr2uvfits.c uvfits.c -lcfitsio -lsla -lm

mwacalc: mwacalc.c CALC_xdr.c
	$(CC) $(CFLAGS) -o $@ $^

libsla.a:
	cd SLALIB_C ; make
	rm -f SLALIB_C/*.o

clean:
	rm -f *.o $(TARGETS) libsla.a SLALIB_C/*.o
