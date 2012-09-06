INCS=$(shell python -c "print ' '.join(['-I ' + s for s in '${INCLUDE}'.split(':')])")
all: build_lfiles

build_lfiles: build_lfiles.o mwac_utils.o antenna_mapping.o
	$(CC) build_lfiles.o mwac_utils.o antenna_mapping.o -o build_lfiles ${INCS} -lcfitsio -lm

mwac_utils.o: mwac_utils.c
	$(CC)  -c mwac_utils.c

build_lfiles.o: build_lfiles.c
	$(CC) ${INCS} -c build_lfiles.c 

antenna_mapping.o: antenna_mapping.c
	$(CC) -c antenna_mapping.c 

clean:
	rm -f *.o build_lfiles


