CFITSIO_INCS=$(shell pkg-config --silence-errors --cflags cfitsio)
CFITSIO_LIBS=$(shell pkg-config --silence-errors --libs cfitsio)
INCS=$(shell python -c "if len('${INCLUDE}')>0:print ' '.join(['-I ' + s for s in '${INCLUDE}'.split(':')])")
INCS+=$(CFITSIO_INCS)
CFLAGS+=-Wall -O -g

all: build_lfiles read_mwac

read_mwac: read_mwac.c
	$(CC) $(CFLAGS) $(INCS) read_mwac.c -o read_mwac $(CFITSIO_LIBS) -lm

build_lfiles: build_lfiles.c mwac_utils.o antenna_mapping.o
	$(CC) $(CFLAGS) $(INCS) build_lfiles.c mwac_utils.o antenna_mapping.o -o build_lfiles $(CFITSIO_LIBS) -lm

mwac_utils.o: mwac_utils.c
	$(CC) $(CFLAGS) -c mwac_utils.c

antenna_mapping.o: antenna_mapping.c
	$(CC) $(CFLAGS) -c antenna_mapping.c 

clean:
	rm -f *.o build_lfiles read_mwac

