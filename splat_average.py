"""
splat DAS inputs and (optionally) average in time

python ~/mwa/MWA_Tools/splat_average.py -r P00-drift_121_20110927130001 -o test -c 121 -v -a 8
# INFO:splat_average: Channel order: 109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,132,131,130,129
# INFO:splat_average: AC size for DAS 1: 14548992 bytes
# INFO:splat_average: CC size for DAS 1: 916586496 bytes
# INFO:splat_average: Num integrations in AC for DAS 1: 296
# INFO:splat_average: Num integrations in CC for DAS 1: 296
# INFO:splat_average: AC size for DAS 2: 14548992 bytes
# INFO:splat_average: CC size for DAS 2: 916586496 bytes
# INFO:splat_average: Num integrations in AC for DAS 2: 296
# INFO:splat_average: Num integrations in CC for DAS 2: 296
# INFO:splat_average: AC size for DAS 3: 14548992 bytes
# INFO:splat_average: CC size for DAS 3: 916586496 bytes
# INFO:splat_average: Num integrations in AC for DAS 3: 296
# INFO:splat_average: Num integrations in CC for DAS 3: 296
# INFO:splat_average: AC size for DAS 4: 14548992 bytes
# INFO:splat_average: CC size for DAS 4: 916586496 bytes
# INFO:splat_average: Num integrations in AC for DAS 4: 296
# INFO:splat_average: Num integrations in CC for DAS 4: 296
# INFO:splat_average: Averaging output by factor of 8
# INFO:splat_average: SPLAT and averaging AC...
# INFO:splat_average: Opened AC file for DAS 1: P00-drift_121_20110927130001_das1.LACSPC
# INFO:splat_average: Opened AC file for DAS 2: P00-drift_121_20110927130001_das2.LACSPC
# INFO:splat_average: Opened AC file for DAS 3: P00-drift_121_20110927130001_das3.LACSPC
# INFO:splat_average: Opened AC file for DAS 4: P00-drift_121_20110927130001_das4.LACSPC
# INFO:splat_average: Writing AC output to test.av.lacspc
# INFO:splat_average: SPLAT and averaging CC...
# INFO:splat_average: Opened CC file for DAS 1: P00-drift_121_20110927130001_das1.LCCSPC
# INFO:splat_average: Opened CC file for DAS 2: P00-drift_121_20110927130001_das2.LCCSPC
# INFO:splat_average: Opened CC file for DAS 3: P00-drift_121_20110927130001_das3.LCCSPC
# INFO:splat_average: Opened CC file for DAS 4: P00-drift_121_20110927130001_das4.LCCSPC
# INFO:splat_average: Writing CC output to test.av.lccspc


"""


import sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob
from optparse import OptionParser
import numpy

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('splat_average')
logger.setLevel(logging.WARNING)


_CHANSPERDAS=192
_CHANSPERCOARSE=32
_NDAS=4
# 32 antennas * 2 polns
_NINP=64

######################################################################
def main():

    usage="Usage: %prog [options]\n"
    usage+="\tsplat DAS inputs and (optionally) average in time\n"
    usage+="\tpython ~/mwa/MWA_Tools/splat_average.py -r P00-drift_121_20110927130001 -o test -c 121 -v -a 8\n"


    parser = OptionParser(usage=usage)
    parser.add_option('-c','--center',dest='center_channel',default=100,type=int,
                      help='Center channel of observation')
    parser.add_option('-a','--average',dest='n_av',default=1,type=int,
                      help='Number of time samples to average [default=%default]')
    parser.add_option('-o','--output',dest='outroot',default='',
                      help='Root name of output [default=input root]')
    parser.add_option('-r','--root',dest='root',default='',
                      help='Root name of input')
    parser.add_option('-i','--inputs',dest='inputs',default=_NINP,
                      help='Number of input correlator streams (2*number of anteannas) [default=%default]')
    parser.add_option('-d','--das',dest='das',default=_NDAS,
                      help='Number of DASs [default=%default]')

    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")
    

    (options, args) = parser.parse_args()

    if (options.verbose):
        logger.setLevel(logging.INFO)
    if len(options.root)==0:
        logger.error('Must specify input root')
        sys.exit(1)
    if len(options.outroot)==0:
        options.outroot=options.root

    correct_chan=channel_order(options.center_channel)
    if (correct_chan is None):
        sys.exit(2)
    try:
        fnames_ac,fnames_cc,n_times=get_filenames_integrations(options.root, options.das)
    except:
        sys.exit(2)

    if (options.n_av>1):
        outname_ac=options.outroot + '.av.lacspc'
        outname_cc=options.outroot + '.av.lccspc'
        logger.info('Averaging output by factor of %d' % options.n_av)
    else:
        outname_ac=options.outroot + '.lacspc'
        outname_cc=options.outroot + '.lccspc'
        
    logger.info('SPLAT and averaging AC...')
    retval=splat_average_ac(fnames_ac, outname_ac, n_times, 
                            options.das*_CHANSPERDAS, options.inputs, 
                            options.n_av, correct_chan)
    if retval is None:
        logger.error('Error writing AC file')
        sys.exit(2)

    
    logger.info('SPLAT and averaging CC...')
    retval=splat_average_cc(fnames_cc, outname_cc, n_times, 
                            options.das*_CHANSPERDAS, options.inputs, 
                            options.n_av, correct_chan)

    if retval is None:
        logger.error('Error writing CC file')
        sys.exit(2)
######################################################################
def channel_order(center_channel):
    """
    correct_chan=channel_order(center_channel)
    gives the mapping between the input channels and the correct order
    depends on the center channel
    will return an array with length either to the number of coarse PFB channels
    """
    if (center_channel <= 12 or center_channel > 243):
        logger.error('Center channel must be between 13 and 243')
        return None
    correct_chan=numpy.zeros((24,),dtype=int)
    # Calculate the output channel order.
    minchan=center_channel-12
    nbank1=0
    nbank2=0
    for ii in xrange(minchan, minchan+24):
        if (ii<=128):
            nbank1+=1
        else:
            nbank2+=1
    for ii in xrange(nbank1):
        correct_chan[ii]=ii
    for ii in xrange(nbank2):
        correct_chan[ii+nbank1]=23-ii
    
    logger.info('Channel order: %s' % (','.join([str(x) for x in (minchan+correct_chan)])))
    return correct_chan
######################################################################
def get_filenames_integrations(root, ndas):
    """
    fnames_ac,fnames_cc,n_times=get_filenames_integrations(root, ndas)

    given a root, will search for <root>_das[1234].lacspc and <root>_das[1234].lccspc
    or with .LACSPC, .LCCSPC

    returns the names of the AC and CC files, along with the number of integrations

    will look for <ndas> files
    """
    acsize=[]
    n_times_ac=[]
    fin_cc=[]
    ccsize=[]
    n_times_cc=[]
    fnames_ac=[]
    fnames_cc=[]
    for k in xrange(ndas):
        fname_ac=root + ('_das%d.LACSPC' % (k+1))
        fname_cc=root + ('_das%d.LCCSPC' % (k+1))
        if (not os.path.exists(fname_ac)):
            fname_ac=root + ('_das%d.lacspc' % (k+1))
            fname_cc=root + ('_das%d.lccspc' % (k+1))
        fnames_ac.append(fname_ac)
        fnames_cc.append(fname_cc)
        # get file sizes
        try:
            acsize.append(os.path.getsize(fname_ac))
            logger.info("AC size for DAS %d: %d bytes" % (k+1,acsize[-1]))
        except:
            logger.error('Cannot find AC file for DAS %d' % (k+1))
            return None
        try:
            ccsize.append(os.path.getsize(fname_cc))
            logger.info("CC size for DAS %d: %d bytes" % (k+1,ccsize[-1]))
        except:
            logger.error('Cannot find CC file for DAS %d' % (k+1))
            return None
        n_times_ac.append(acsize[-1]/((_CHANSPERDAS)*_NINP*4))
        # CC needs two floats since data are complex
        n_times_cc.append(ccsize[-1]/(_CHANSPERDAS*_NINP*(_NINP-1)/2*8))
        logger.info("Num integrations in AC for DAS %d: %d" % (k+1,n_times_ac[-1]))
        logger.info("Num integrations in CC for DAS %d: %d" % (k+1,n_times_cc[-1]))
        if (n_times_ac[k] != n_times_cc[k]):
            logger.error('AC integrations for DAS %d (%d) does not match CC integrations for DAS %d (%d)' % (
                    k+1,n_times_ac[k],k+1,n_times_cc[k]))
            return None
                       
        if (k>0):
            if n_times_ac[k] != n_times_ac[k-1]:
                logger.error('AC integrations for DAS %d (%d) does not match that for DAS %d (%d)' % (
                    k+1,n_times_ac[k],k,n_times_ac[k-1]))
                return None
    return fnames_ac,fnames_cc,n_times_ac[0]
    
######################################################################
def splat_average_ac(innames, outname, ntimes, nchan, ninp, n_av, correct_chan):
    """
    result=splat_average_ac(innames, outname, ntimes, nchan, ninp, n_av, correct_chan)
    innames is a list of input AC filenames
    outname is the output file
    ntimes is the number of integrations
    nchan is the total number of channels (over all DASs)
    ninp is the number of correlator inputs (2*antennas)
    n_av is the number of integrations to average (>=1)
    correct_chan is the mapping between input channel order and correct order

    if result is not None, success
    """
    
    fin_ac=[]
    ndas=len(innames)
    for k in xrange(ndas):
        try:
            fin_ac.append(open(innames[k],'rb'))
            logger.info('Opened AC file for DAS %d: %s' % (k+1,innames[k]))
        except:
            logger.error('Cannot open AC file for DAS %d: %s' % (k+1,innames[k]))
            return None
    if (os.path.exists(outname)):
        os.remove(outname)
    try:
        fout_ac=open(outname,'wb')
        logger.info('Writing AC output to %s' % outname)
    except:
        logger.error('Could not open AC file %s for writing' % outname)
        return None
    indata=numpy.zeros((ninp,nchan),dtype=numpy.float32)
    outdata=numpy.zeros((ninp,nchan),dtype=numpy.float32)
    if (n_av>1):
        D=numpy.zeros((n_av,ninp,nchan),dtype=numpy.float32)
        shape=D.shape
    i=0
    chanperdas=nchan/ndas
    chanpercoarse=nchan/len(correct_chan)
    for t in xrange(ntimes):
        for k in xrange(ndas):
            indata[:,k*chanperdas:(k+1)*chanperdas]=numpy.fromfile(file=fin_ac[k],
                                                                   dtype=numpy.float32,
                                                                   count=chanperdas*ninp).reshape((ninp,chanperdas))
            
        for j in xrange(24):
            outdata[:,j*chanpercoarse:(j+1)*chanpercoarse]=indata[
                :,correct_chan[j]*chanpercoarse:(correct_chan[j]+1)*chanpercoarse]
        if n_av>1:
            D[i]=outdata
        else:
            outdata.tofile(fout_ac)
        if n_av>1:
            i+=1
            if (i>=n_av):
                Dav=D.mean(axis=0)
                Dav.tofile(fout_ac)
                i=0

    for k in xrange(ndas):
        fin_ac[k].close()

    fout_ac.close()
    return True

######################################################################
def splat_average_cc(innames, outname, ntimes, nchan, ninp, n_av, correct_chan):
    """
    result=splat_average_cc(innames, outname, ntimes, nchan, ninp, n_av, correct_chan)
    innames is a list of input CC filenames
    outname is the output file
    ntimes is the number of integrations
    nchan is the total number of channels (over all DASs)
    ninp is the number of correlator inputs (2*antennas)
    n_av is the number of integrations to average (>=1)
    correct_chan is the mapping between input channel order and correct order

    if result is not None, success
    """
    fin_cc=[]
    ndas=len(innames)
    for k in xrange(ndas):
        try:
            fin_cc.append(open(innames[k],'rb'))
            logger.info('Opened CC file for DAS %d: %s' % (k+1,innames[k]))
        except:
            logger.error('Cannot open CC file for DAS %d: %s' % (k+1,innames[k]))
            return None
    if (os.path.exists(outname)):
        os.remove(outname)
    try:
        fout_cc=open(outname,'wb')
        logger.info('Writing CC output to %s' % outname)
    except:
        logger.error('Could not open CC file %s for writing' % outname)
        return None
    # two because they are complex
    indata=numpy.zeros((ninp*(ninp-1)/2,nchan*2,),dtype=numpy.float32)
    outdata=numpy.zeros((ninp*(ninp-1)/2,nchan*2,),dtype=numpy.float32)
    if (n_av>1):
        D=numpy.zeros((n_av,ninp*(ninp-1)/2,nchan*2),dtype=numpy.float32)
        shape=D.shape
    i=0
    chanperdas=nchan/ndas
    chanpercoarse=nchan/len(correct_chan)
    for t in xrange(ntimes):
        for k in xrange(ndas):
            indata[:,k*chanperdas*2:(k+1)*chanperdas*2]=numpy.fromfile(file=fin_cc[k],
                                                                       dtype=numpy.float32,
                                                                       count=chanperdas*2*ninp*(ninp-1)/2).reshape((ninp*(ninp-1)/2,chanperdas*2))
                
        for j in xrange(24):
            outdata[:,j*chanpercoarse*2:(j+1)*chanpercoarse*2]=indata[
        :,correct_chan[j]*chanpercoarse*2:(correct_chan[j]+1)*chanpercoarse*2]
        if n_av>1:
            D[i]=outdata
        else:
            outdata.tofile(fout_cc)
        if n_av>1:
            i+=1
            if (i>=n_av):
                Dav=D.mean(axis=0)
                Dav.tofile(fout_cc)
                i=0
    for k in xrange(ndas):
        fin_cc[k].close()

    fout_cc.close()
    return True

######################################################################

if __name__=="__main__":
    main()
