# Makefile for corr2uvfits.

CFLAGS=-g -O -Wall -D_FILE_OFFSET_BITS=64 -L. 
CFITSIO_INCS=$(shell pkg-config --silence-errors --cflags cfitsio)
CFITSIO_LIBS=$(shell pkg-config --silence-errors --libs cfitsio)

# Hacks for people who have installed cfitsio themselves instead of using a package manager
INCS=$(shell python -c "if len('${INCLUDE}')>0:print ' '.join(['-I ' + s for s in '${INCLUDE}'.split(':')])")
ifneq ($(strip $(CFITSINC)),)
INCS += -I$(CFITSINC)
endif
ifneq ($(strip $(CFITSLIB)),)
INCS += -L$(CFITSLIB)
endif

TARGETS=corr2uvfits Lphasor test_readuvfits
SRCDIR=CONV2UVFITS


all: $(TARGETS)

corr2uvfits: corr2uvfits.c convutils.c convutils.h uvfits.c uvfits.h libsla.a
	ranlib libsla.a
	cc $(CFLAGS) $(INCS) $(CFITSIO_INCS) -o corr2uvfits corr2uvfits.c convutils.c uvfits.c $(CFITSIO_LIBS) -lcfitsio -lsla -lm

Lphasor: Lphasor.c convutils.c convutils.h libsla.a uvfits.c
	ranlib libsla.a
	cc $(CFLAGS) $(INCS) $(CFITSIO_INCS) -o Lphasor Lphasor.c convutils.c uvfits.c -lsla $(CFITSIO_LIBS) -lcfitsio -lm

test_readuvfits: test_readuvfits.c uvfits.c libsla.a
	ranlib libsla.a
	cc $(CFLAGS) $(INCS) $(CFITSIO_INCS) -o $@ $^ $(CFITSIO_LIBS) -lcfitsio -lsla -lm

libsla.a:
	cd SLALIB_C ; make
	rm -f SLALIB_C/*.o
clean:
	rm -f *.o $(TARGETS) libsla.a SLALIB_C/*.o 
	rm -rf corr2uvfits.dSYM
