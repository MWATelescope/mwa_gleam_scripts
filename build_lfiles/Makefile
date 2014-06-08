CFLAGS=-g -O -Wall -D_FILE_OFFSET_BITS=64
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

all: build_lfiles read_mwac uvcompress

read_mwac: read_mwac.o  
	$(CC) $(CFLAGS) read_mwac.o -o read_mwac ${INCS} $(CFITSIO_LIBS) -lcfitsio -lm

build_lfiles: build_lfiles.o mwac_utils.o antenna_mapping.o
	$(CC) $(CFLAGS) $(CFITSIO_INCS) -fopenmp build_lfiles.o mwac_utils.o antenna_mapping.o -o build_lfiles ${INCS} $(CFITSIO_LIBS) -lcfitsio -lm -lpthread

uvcompress: compress.cpp uvcompress.cpp
	$(CXX) $(CFLAGS) $(CFITSIO_INCS) -o $@ $^ ${INCS} $(CFITSIO_LIBS) -lcfitsio -lm

mwac_utils.o: mwac_utils.c
	$(CC) $(CFLAGS) -fopenmp  -c mwac_utils.c

build_lfiles.o: build_lfiles.c
	$(CC) $(CFLAGS) $(CFITSIO_INCS) ${INCS} -c build_lfiles.c 

read_mwac.o: read_mwac.c
	$(CC) $(CFLAGS) $(CFITSIO_INCS) ${INCS} -c read_mwac.c 

antenna_mapping.o: antenna_mapping.c
	$(CC) $(CFLAGS) -c antenna_mapping.c 

clean:
	rm -f *.o build_lfiles read_mwac uvcompress

