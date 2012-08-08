#ifndef __DIFX_CALC_H__
#define __DIFX_CALC_H__

#include "CALCServer.h"

typedef struct
{
	int order;
	char *calcServer;
	int calcProgram;
	int calcVersion;
	struct getCALC_arg request;
	CLIENT *clnt;
} CalcParams;

#endif
