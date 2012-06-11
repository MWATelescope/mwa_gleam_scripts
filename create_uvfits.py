"""
create_uvfits.py

standalone program to create UVFITS files for MWA 32T data
based on elements of image_32T.py
can operate from:
 individual das output files
 averaged correlator output

Example:
python ~/mwa/MWA_Tools/create_uvfits.py --inttime=8 -r test --force --image P00-drift_121_20110927130001_das?.LACSPC P00-drift_121_20110927130001_das?.LCCSPC

uses class:
Corr2UVFITS
takes software correlator output
converts to uvfits
needs various metadata to get the times/positions right

"""


import sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob
import bisect
from optparse import OptionParser,OptionGroup
import ephem
import pyfits
from mwapy import ephem_utils
try:
    from obssched.base import schedule
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)
try:
    import primarybeammap
    _useplotting=True
except ImportError:
    _useplotting=False    
    
import splat_average, get_observation_info
import numpy

instr_config_master='instr_config_32T.txt'
antenna_locations_master='antenna_locations_32T.txt'
static_mask_master='mask_pfb_32T.txt'

_CHANSPERDAS=192
_CHANSPERCOARSE=32
_NDAS=4
# 32 antennas * 2 polns
_NINP=64

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('create_uvfits')
logger.setLevel(logging.WARNING)

# open up database connection
try:
    db = schedule.getdb()
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)

######################################################################
# external routines
# the value after is 1 (if critical) or 0 (if optional)
external_programs={'corr2uvfits': 1}
                   
# go through and find the external routines in the search path
# or $MWA_PATH
searchpath=os.environ.get('MWA_PATH')
if (searchpath is not None):
    searchpath=searchpath.split(':')
else:
    searchpath=[]
external_paths={}
for external_program in external_programs.keys():
    external_paths[external_program]=None
    p=subprocess.Popen('which %s' % external_program, shell=True,stderr=subprocess.PIPE,
                       stdout=subprocess.PIPE, close_fds=True)
    (result,result_error)=p.communicate()
    if (len(result) > 0):
        # it was found
        external_paths[external_program]=result.rstrip("\n")
    else:
        for path in searchpath:
            if (os.path.exists(path + '/' + external_program)):
                external_paths[external_program]=path + '/' + external_program
    if (external_paths[external_program] is None):
        # was not found anywhere
        logger.warning('Unable to find external program %s; please set your MWA_PATH environment variable accordingly',external_program)
        if (external_programs[external_program]):
            logger.error('External program %s is required; exiting',external_program)
            sys.exit(1)
    else:
        logger.debug('Found %s=%s',external_program,external_paths[external_program])
   
    

        
######################################################################
def main():
    cwd=os.path.abspath(os.getcwd()) + '/'
    basedir=cwd

    dir=os.path.dirname(__file__)
    if (len(dir)==0):
        dir='.'
    dir+='/'

    usage="Usage: %prog [options] file_das1.LACSPC file_das2.LACSPC ... file_das1.LCCSPC file_das2.LCCSPC...\n"
    usage+="\tNeeds an autocorrelation (.LACSPC) and crosscorrelation (.LCCSPC) file for each DAS\n"
    usage+="\tTries to determine basic information about the observation from the filename, but can specify <DATETIME> or <GPS> to override\n"
    usage+="\tSame with RA,Dec\n"
    usage+="\tRequires external programs %s for operation; searches $MWA_PATH for these\n" % (", ".join(external_programs.keys()))    
    usage+="\nExample:\n\tpython ~/mwa/MWA_Tools/create_uvfits.py --inttime=8 --force -v --image P00-drift_121_20110927130001_das?.LACSPC P00-drift_121_20110927130001_das?.LCCSPC\n"

    parser = OptionParser(usage=usage)
    
    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")
    parser.add_option('-r','--root',dest='root',default='',
                      help='Root name of input')
    parser.add_option('--inttime',dest='inttime',default=1,type=int,
                      help='Specify integration time in seconds; >1 indicates averaging [default: %default]')
    parser.add_option('--object',dest='objectname',default='',
                      help='Specify object name')
    parser.add_option('--image',action="store_true",dest="image",default=False,
                      help="Generate an image for this pointing?")
    parser.add_option('--force',dest='force',action='store_true',default=False,
                      help='Force regeneration of files?')

    extragroup=OptionGroup(parser,'Extra Options',
                           "These will override default behavior")
    
    extragroup.add_option('--autoflag',dest='autoflag',default=True,
                      help='Use autoflagging in corr2uvfits? [default: %default]')
    extragroup.add_option('--instr',dest='instrument_config',default=dir + instr_config_master,
                      help='Specify the instrument configuration file [default: %default]')
    extragroup.add_option('--antenna',dest='antenna_locations',default=dir + antenna_locations_master,
                      help='Specify the antenna locations file [default: %default]')
    extragroup.add_option('--flag',dest='static_flag',default=dir + static_mask_master,
                      help='Specify a static masking file for the channels [default: %default]')
    extragroup.add_option('--ra','--RA',dest='ra',default=None,
                      help='Phase center RA (decimal degrees or HH:MM:SS) [default=lookup/meridian]')
    extragroup.add_option('--dec','--Dec',dest='dec',default=None,
                      help='Phase center Dec (decimal degrees or DD:MM:SS) [default=lookup/zenith]')
    extragroup.add_option('-d','--datetime',dest="datetimestring",
                      help="Search for information on <DATETIME> (YYYYMMDDhhmmss) [default=lookup]",
                      metavar="DATETIME")
    extragroup.add_option('-g','--gps',dest="gpstime",
                      help="Search for information on <GPS> (s)  [default=lookup]",type='int',
                      metavar="GPS")
    extragroup.add_option('-m','--maxdiff',dest="maxtimediff",type='int',
                      help="Maximum time difference for search (in sec)", default=10)
    extragroup.add_option('--timeoffset',dest='timeoffset',default=2,type=int,
                      help='Specify time offset in seconds between the file datetime and the observation starttime [default: %default]')
    extragroup.add_option('--conjugate',dest='conjugate',default=True,
                      help='Conjugate correlator input [default: %default]')
    extragroup.add_option('--correlator',dest='correlator',default='H',
                      choices=['H','S'],
                      help='Specify hardware (H) or software (S) correlator [default: %default]')
    parser.add_option_group(extragroup)
    
    (options, args) = parser.parse_args()
    if (options.ra is not None):
        ra=parse_RA(options.ra)
    else:
        ra=None
    if (options.dec is not None):
        dec=parse_Dec(options.dec)
    else:
        dec=None
    autoflag=options.autoflag
    force=options.force
    conjugate=options.conjugate
    correlator=options.correlator
    objectname=options.objectname
    inttime=options.inttime
    timeoffset=options.timeoffset
    if (options.verbose):
        logger.setLevel(logging.INFO)

    # determine the antenna_locations file
    if ('/' in options.antenna_locations):
        antenna_locations=options.antenna_locations
    else:
        antenna_locations=cwd + options.antenna_locations
    if not os.path.exists(antenna_locations):
        logger.error('Unable to find antenna_locations file %s' % antenna_locations)
        sys.exit(2)
    # determine the instrument_configuration file
    if ('/' in options.instrument_config):
        instrument_configuration=options.instrument_config
    else:
        instrument_configuration=cwd + options.instrument_configuration
    if not os.path.exists(instrument_configuration):
        logger.error('Unable to find instrument_configuration file %s' % instrument_configuration)
        sys.exit(2)

    # determine the static flagging file
    if ('/' in options.static_flag):
        static_flag=options.static_flag
    else:
        static_flag=cwd + options.static_flag
    if not os.path.exists(static_flag):
        logger.error('Unable to find static_flag file %s' % static_flag)
        sys.exit(2)

    files=args
    if len(files)<2*_NDAS:
        logger.error('Must supply %d files for input' % (2*_NDAS))
        sys.exit(2)
    if (len(options.root)==0 or options.root is None):
        options.root=re.sub('_das\d\..*','',files[0])
        options.root=os.path.split(options.root)[-1]
        logger.warning('No output root specified; will use %s' % options.root)

    # get the basic time/pointing information
    observation_num=None
    try:
        # check if a datetimestring is input
        if observation_num is None and options.datetimestring is not None:
            observation_num=find_observation_num(options.datetimestring, maxdiff=options.maxtimediff, db=db)
            if observation_num is None:
                logger.error('No matching observation found for datetimestring=%s\n' % (options.datetimestring))
        # check if a GPS time is input
        if observation_num is None and options.gpstime is not None:
            observation_num=find_closest_observation((options.gpstime),maxdiff=options.maxtimediff,db=db)
            if observation_num is None:
                logger.error('No matching observation found for gpstime=%d\n' % (options.gpstime))
        if observation_num is None:
            # try to parse the input filename
            observation_num=get_observation_info.find_observation_num(files[0], maxdiff=options.maxtimediff, db=db)
    except:
        logger.error('Error trying to match observation in database')
        

    if observation_num is None:
        logger.error('No matching observation found for filename=%s\n' % (options.filename))
        sys.exit(1)
    try:
        observation=get_observation_info.MWA_Observation(observation_num,db=db)
    except:
        logger.error('Error retrieving observation info for %d' % observation_num)
        sys.exit(1)
    print "\n##############################"
    print observation
    print "##############################\n"
    if (options.image):
        if (not _useplotting):
            logger.warning('Unable to import primarybeammap to generate image\n')
        else:
            datetimestring='%04d%02d%02d%02d%02d%02d' % (observation.year,observation.month,
                                                         observation.day,
                                                         observation.hour,observation.minute,
                                                         observation.second)


            logger.info('Creating sky image for %04d/%02d/%02d %02d:%02d:%02d, %.2f MHz, delays=%s' % (
                observation.year,observation.month,observation.day,
                observation.hour,observation.minute,observation.second,
                channel2frequency(observation.center_channel),
                ','.join([str(x) for x in observation.delays])))
            result=primarybeammap.make_primarybeammap(datetimestring, observation.delays,
                                                      frequency=channel2frequency(observation.center_channel),
                                                      center=True,
                                                      title=observation.filename)
            if (result is not None):
                logger.info("Wrote %s" % result)

    instr_config_localsource=True
    if instr_config_master in instrument_configuration:
        # need to construct it from the master
        out_instrument_configuration=get_instr_config(observation_num, instrument_configuration)
        if (out_instrument_configuration is None):
            logger.error('Unable to generate instr_config file for GPS time %d from %s' % (observation_num, instrument_configuration))
            sys.exit(2)
        out_instrument_configuration_name='instr_config_%d.txt' % (observation_num)
        instr_config_localsource=False
        if (os.path.exists(out_instrument_configuration_name)):
            os.remove(out_instrument_configuration_name)
        fout=open(out_instrument_configuration_name,'w')
        fout.write(out_instrument_configuration)
        fout.close()
        logger.info('Wrote instr_config to %s' % (out_instrument_configuration_name))
        instrument_configuration=out_instrument_configuration_name


    # try to get pointing information from database lookup
    if ra is None and observation.RA is not None:
        ra=parse_RA(str(observation.RA))
        dec=parse_Dec(str(observation.Dec))
        logger.info('Setting (RA,Dec) to (%s, %s)' % (ra,dec))

    # determine number of time samples
    ntimes=0
    if ('LACSPC' in files[0].upper()):
        acsize=os.path.getsize(files[0])
        ntimes=acsize/((_CHANSPERDAS)*_NINP*4)
    elif ('LCCSPC' in files[0].upper()):
        ccsize=os.path.getsize(files[0])        
        ntimes=ccsize/(_CHANSPERDAS*_NINP*(_NINP-1)/2*8)
    if ntimes == 0:
        logger.error('Unable to get number of integrations')
        sys.exit(2)
    logger.info('Found %d integrations in file %s' % (ntimes,files[0]))

    # figure out the files for AC and CC for each DAS
    ac_names=['']*_NDAS
    cc_names=['']*_NDAS
    for filename in files:
        dasnumber=int(re.sub('\..*','',re.sub('.*?das','',filename)))
        if ('LACSPC' in filename.upper()):
            ac_names[dasnumber-1]=filename
        if ('LCCSPC' in filename.upper()):
            cc_names[dasnumber-1]=filename

    for k in xrange(_NDAS):
        if len(ac_names[k])==0 or not os.path.exists(ac_names[k]):
            logger.error('Cannot find AC file for DAS %d: %s' % (k,ac_names[k]))
            sys.exit(2)
        if len(cc_names[k])==0 or not os.path.exists(cc_names[k]):
            logger.error('Cannot find CC file for DAS %d: %s' % (k,cc_names[k]))
            sys.exit(2)
                         
    if (inttime>1):
        outname_ac=options.root + '.av.lacspc'
        outname_cc=options.root + '.av.lccspc'
        logger.info('Averaging output by factor of %d' % inttime)
    else:
        outname_ac=options.root + '.lacspc'
        outname_cc=options.root + '.lccspc'

    # determine the channel ordering
    correct_chan=splat_average.channel_order(observation.center_channel)
    
    if (not os.path.exists(outname_ac) or force):
        if os.path.exists(outname_ac):
            logger.warning('AC file %s exists, but force=yes' % outname_ac)
        
        logger.info('SPLAT and averaging AC...')
        retval=splat_average.splat_average_ac(ac_names, outname_ac, ntimes, 
                                              _NDAS*_CHANSPERDAS, 
                                              _NINP, 
                                              inttime, correct_chan)
        if retval is None:
            logger.error('Error writing AC file')
            sys.exit(2)
        logger.info('Wrote %s' % outname_ac)
    else:
        if os.path.exists(outname_ac):
            logger.info('AC file %s exists: not overwriting' % (outname_ac))
    if (not os.path.exists(outname_cc) or force):
        if os.path.exists(outname_cc):
            logger.warning('CC file %s exists, but force=yes' % outname_cc)
        logger.info('SPLAT and averaging CC...')
        retval=splat_average.splat_average_cc(cc_names, outname_cc, ntimes, 
                                              _NDAS*_CHANSPERDAS, 
                                              _NINP, 
                                              inttime, correct_chan)
        if retval is None:
            logger.error('Error writing CC file')
            sys.exit(2)
        logger.info('Wrote %s' % outname_cc)
    else:
        if os.path.exists(outname_cc):
            logger.info('CC file %s exists: not overwriting' % (outname_cc))

    corr2uvfits=Corr2UVFITS(basename=options.root,RA=ra,Dec=dec,
                            year=observation.year,month=observation.month,
                            day=observation.day, 
                            time='%02d:%02d:%02d' % (observation.hour,observation.minute,observation.second),
                            channel=observation.center_channel,
                            objectname=objectname,inttime=inttime,
                            flag=autoflag,
                            flagfile=static_flag,
                            instr_config=instrument_configuration, antenna_locations=antenna_locations,
                            conjugate=conjugate,correlator=correlator,timeoffset=timeoffset,force=force,
                            fake=False)

    if (not corr2uvfits.write_header_file(
            'header_%d.txt' % observation.observation_number)):
        logger.error('Error in writing header file')
        return None
    uvfitsname=corr2uvfits.write_uvfits()
    if (not uvfitsname):
        logger.error('Error in writing UVFITS file')
        return None
    logger.info('%s written!' % (uvfitsname))
    if not options.verbose:
        os.remove(corr2uvfits.headername)
        if not instr_config_localsource:
            os.remove(instrument_configuration)
                
            
##################################################
class Corr2UVFITS:
##################################################
    """ A class to convert 32T correlator output to UVFITS files
    """

    ##################################################
    def __init__(self,basename=None,objectname=None,RA=None,Dec=None,
                 year=None,month=None,day=None,time=None,channel=None,
                 inttime=1,totaltime=None,flag=0,flagfile=None,
                 antenna_locations=None,instr_config=None,
                 conjugate=0,correlator='s',timeoffset=2,force=False,fake=None):
        """
        __init__(self,basename=None,objectname=None,RA=None,Dec=None,
                 year=None,month=None,day=None,time=None,channel=None,
                 inttime=1,totaltime=None,flag=0,flagfile=None,
                 antenna_locations=None,instr_config=None,
                 conjugate=0,correlator='s',timeoffset=2,force=False,fake=None)
        allows setting of various parameters for conversion to uvfits files
        RA in decimal hours
        Dec in decimal degrees
        correlator='s' or 'h' for hardware vs. software
        """

        # executable
        self.corr2uvfits=external_paths['corr2uvfits']
        result=runit("%s -v" % self.corr2uvfits,verbose=0)
        try:
            self.revision=int(result[0][0].split()[-2])
        except:
            self.revision=0
    
        curpath=os.path.abspath(os.getcwd())

        self.antenna_locations=antenna_locations
        self.instr_config=instr_config

        # defaults for the things we do not change
        # set some values from instr_config or the file itself
        self.n_inputs=0
        if (correlator == 's' or correlator == 'S'):
            # software correlator
            # 128 channels, 1.28 MHz total bandwidth
            self.n_chans=128
            self.bandwidth=1.28
            self.correlator='S'
        else:
            # hardware correlator
            # 768 channels (4 DASs)
            # 30.72 MHz total bandwidth
            self.n_chans=768
            self.bandwidth=30.72
            self.correlator='H'
        self.invert_freq=0
        self.n_scans=0

        self.basename=basename
        self.objectname=objectname
        self.RA=RA
        self.Dec=Dec
        self.inttime=inttime
        #self.totaltime=totaltime
        self.flag=flag
        self.conjugate=conjugate
        self.flagfile=flagfile
        # offset between file name and actual start time
        # in seconds
        self.timeoffset=timeoffset

        self.year=year
        self.month=month
        self.day=int(day)
        self.channel=channel
        self.time=time


        if (self.year is not None and self.month is not None and self.day is not None and self.time is not None):
            self.datetime=datetime.datetime(self.year,self.month,self.day,
                                            int(self.time[0:2]),
                                            int(self.time[3:5]),
                                            int(self.time[6:8]))+datetime.timedelta(seconds=self.timeoffset)
            # this should correctly handle boundaries
            self.year,self.month,self.day=self.datetime.year,self.datetime.month,self.datetime.day
            self.time=self.datetime.strftime('%H:%M:%S')

        # processing steps
        self.basename_processed=0
        self.has_headerfile=0
        self.headername=None

        self.HA=None

        self.fake=fake
        self.force=force

        if (self.basename):
            if (not self.process_basename()):
                logger.error('Error processing basename: %s', self.basename)
                

    ##################################################
    def process_basename(self):
        """
        process_basename(self)
        based on the input filename computes date and time
        from that it and the RA of the source it computes the HA (hrs)
        returns 1 on success
        """
        if (self.inttime > 1):
            suffix='.av'
        else:
            suffix=''
        if (self.basename):
            self.ccname=self.basename + suffix + ".LCCSPC"
            self.acname=self.basename + suffix +".LACSPC"
            # try an alternate extension
            if (not os.path.exists(self.ccname)):
                self.ccname=self.basename + suffix +".lccspc"
                self.acname=self.basename + suffix +".lacspc"
            if (not os.path.exists(self.ccname)):
                logger.error('Cannot access CC file: %s',self.ccname)                
                return None

            s=self.basename.split('_')
            if (self.year is None or self.month is None or self.day is None or self.channel is None or self.datetime is None):
                try:
                    [datetime_str,self.year,self.month,self.day,time,self.channel]=self.parse_basename()
                except:
                    logger.error('Unable to parse root name %s' % self.basename)
                    return None
                try:
                    self.datetime=datetime.datetime(self.year,self.month,
                                                    self.day,
                                                    int(time[0:2]),
                                                    int(time[2:4]),
                                                    int(time[4:6]))+datetime.timedelta(seconds=self.timeoffset)
                    # this should correctly handle boundaries
                    self.year,self.month,self.day=self.datetime.year,self.datetime.month,self.datetime.day
                    self.time=self.datetime.strftime('%H:%M:%S')
                except (IndexError,ValueError),err:
                    logger.error('Unable to parse time: %s\n%s', time,err)
                    self.basename_processed=0
                    return
            # even though ct2lst talks about local time, actually we pass it UT
            self.lst=ct2lst_mwa((self.year),(self.month),(self.day),self.time)
            LST=ephem_utils.dec2sexstring(self.lst,digits=0,roundseconds=0)
            mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
            if (self.RA is None):
                logger.warning('No RA specific; using meridian=%s' % (LST))
                self.RA=LST
                RAs=LST
            else:
                RAs=self.RA
            if (self.Dec is None):
                logger.warning('No Dec specific; using zenith=%s' % (ephem_utils.dec2sexstring(mwa.lat)))
                self.Dec=ephem_utils.dec2sexstring(mwa.lat)
                Decs=ephem_utils.dec2sexstring(mwa.lat)
            else:
                Decs=self.Dec
                
            RA=ephem_utils.sexstring2dec(RAs)
            Dec=ephem_utils.sexstring2dec(Decs)            
            self.HA=self.lst-RA
            self.basename_processed=1
            if (self.HA > 12):
                self.HA-=24
            if (self.HA <= -12):
                self.HA+=24

            RAsun,Decsun,Azsun,Altsun=sunposition((self.year),(self.month),(self.day),self.time)
            if (Altsun > 0 and Altsun < 45):
                logger.warning('Sun is at an altitude of %.1f degrees',Altsun)
            elif (Altsun >= 45):
                logger.warning('Sun is at an altitude of %.1f degrees',Altsun)                
            sundist=sundistance(RA*15,Dec,(self.year),(self.month),(self.day),self.time)
            if (sundist < 45):
                logger.warning('Sun is only %.1f degrees away from the field',sundist)
            else:
                logger.info('Sun is %.1f degrees away from the field',sundist)

            if (self.conjugate):
                logger.info('Conjugating correlator input')

        return 1
    ##################################################
    def parse_basename(self):
        """
        [datetime_str,year,month,day,time,channel]=parse_basename()
        basename should have the form of:
        YYYYMMDDHHMMSS_NAME_CHANNEL
        or
        NAME_CHANNEL_YYYYMMDDHHMMSS
        """
        s=self.basename.split('_')
        try:
            datetime_str=s[0]
            sourcename=s[1]
            channel=int(s[2])
            year=int(datetime_str[0:4])
            month=int(datetime_str[4:6])
            day=int(datetime_str[6:8])
            time=datetime_str[8:]            
        except (ValueError,IndexError):
            datetime_str=s[-1]
            sourcename="_".join(s[:-2])
            channel=int(s[-2])
            year=int(datetime_str[0:4])
            month=int(datetime_str[4:6])
            day=int(datetime_str[6:8])
            time=datetime_str[8:]
        return [datetime_str,year,month,day,time,channel]
            
    ##################################################
    def write_header_file(self,outputname='header.txt'):
        """
        write_header_file(self,outputname='header.txt')
        writes the header file header.txt needed by corr2uvfits
        takes some quantities are given, other are computed from the filename
        returns 1 on success
        """
        if (not self.basename_processed):
            logger.error('Must process basename before writing header file')
            return None
        if (not os.path.exists(self.instr_config) and self.instr_config != 'auto'):
            logger.error('Cannot access instr_config template file: %s',
                          self.instr_config)
            logger.error('Must provide instr_config template file')
            return None
        if (not os.path.exists(self.antenna_locations)):
            logger.error('Cannot access antenna_locations template file: %s',
                          self.antenna_locations)
            logger.error('Must provide antenna_locations template file')
            return None

        if (self.flag):
            self.corrtype='B'
        else:
            self.corrtype='B'

        if (self.corrtype=='B' and not os.path.exists(self.acname)):
            logger.error('Cannot access AC file: %s',self.acname)
            return None        

        # get the number of inputs from instr_config file
        try:
            instr_config=open(self.instr_config,'r')
        except IOError,err:
            logger.error('Unable to open instr_config file %s for reading\n%s', self.instr_config,err)
            return None
        result=instr_config.readlines()
        instr_config.close()
        try:
            self.n_inputs=0
            for line in result:
                if (cmp(line,'\n')!=0):
                    s=line.split()
                    if (s[0].startswith('#')==False):
                        # not a comment line
                        if (int(s[0])>self.n_inputs):
                            self.n_inputs=int(s[0])
        except ValueError,err:
            logger.error('Unable to parse instrument configuration file %s (%s):\n%s', self.instr_config,err,line)
            return None
        self.n_inputs+=1 

        # get the number of scans from the size of the ACfile
        # is this correct?  Should check with Randall
        try:
            size=os.path.getsize(self.acname)
        except OSError,err:
            logger.error('Unable to determine size of AC file: %s\n%s',self.acname,err)
            return None
        self.n_scans=size/(int(self.n_chans)*(int(self.n_inputs))*4)
        self.totaltime=self.n_scans*self.inttime
        if (self.n_scans < 2):
            logger.error('Only %d scan(s) present in AC file: %s',self.n_scans,self.acname)
            return None

        # make header.txt
        header=""
        header+="FIELDNAME %s\n" % self.objectname
        header+="N_SCANS   %-3d   # number of scans (time instants) in correlation products\n" % (self.n_scans)
        header+="N_INPUTS  %-3d   # number of inputs into the correlation products\n" % (self.n_inputs)
        header+="N_CHANS   %-3d   # number of channels in spectrum\n" % (self.n_chans)
        header+="CORRTYPE  %s     # correlation type to use. \'C\'(cross), \'B\'(both), or \'A\'(auto)\n" % (self.corrtype)
        header+="INT_TIME  %.1f   # integration time of scan in seconds\n" % (self.inttime)
        # I think this frequency center is correct, based on discussions in Jan 2011
        header+="FREQCENT  %.3f # observing center freq in MHz\n" % (channel2frequency(self.channel))
        header+="BANDWIDTH %.3f  # total bandwidth in MHz\n" % (self.bandwidth)
        # header+="HA_HRS    %.6f   # the HA at the *start* of the scan. (hours)\n" % (self.HA)
        header+="RA_HRS    %.6f   # the RA of the desired phase centre (hours)\n" % (ephem_utils.sexstring2dec(self.RA))
        header+="DEC_DEGS  %.4f   # the DEC of the desired phase centre (degs)\n" % (ephem_utils.sexstring2dec(self.Dec))
        header+="DATE      %d%02d%02d  # YYYYMMDD\n" % (int(self.year),int(self.month),int(self.day))
        header+="TIME      %s      # HHMMSS\n" % (self.time.replace(':',''))
        header+="INVERT_FREQ %d\n" % (self.invert_freq)
        header+="CONJUGATE %d\n" % (self.conjugate)
        
        self.header=header
        try:
            (xdir,xname)=os.path.split(sys.argv[0])
            headerfile=open(outputname,'w')            
            headerfile.write('# corr2uvfits header written by %s\n' % (xname))
            now=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            headerfile.write('# %s\n' % now)
            headerfile.write(header)
            headerfile.close()
            self.has_header_file=1
            logger.info('Header file written to %s' %  outputname)
            self.headername=outputname
        except IOError, err:
            logger.error('Could not write output file: %s', outputname,err)

        return 1

    ##################################################
    def write_uvfits(self,fake=0):
        """
        uvfitsname=write_uvfits(self,fake=0)
        writes the uvfits file from the correlator output, using the header file created  by self.write_header_file()
        if the file exists, will only overwrite if self.force
        """
        if (not self.has_header_file):
            logger.error('No header file written')
            return
        curpath=os.path.abspath(os.getcwd())
        #antenna_dir=os.path.abspath(os.path.dirname(self.antenna_locations))
        #instr_dir=os.path.abspath(os.path.dirname(self.instr_config))

        if (self.flag and not (self.corrtype == 'B')):
            logger.warning('For flagging, correlation type must be \'Both\'')
            self.corrtype='B'
            
        uvfitsname='%s.uvfits' % (self.basename)
        if (self.corrtype == 'B'):
            command=self.corr2uvfits + ' -c %s -a %s' % (self.ccname,self.acname)
        if (self.corrtype == 'C'):
            command=self.corr2uvfits + ' -c %s' % (self.ccname)
        if (self.corrtype == 'A'):
            command=self.corr2uvfits + ' -a %s' % (self.acname)
            
        if (self.corrtype == 'C' or self.corrtype == 'B'):
            if (not os.path.exists(self.ccname)):
                logger.error('Cross correlation file %s does not exist',self.ccname)
                return None
        if (self.corrtype == 'A' or self.corrtype == 'B'):
            if (not os.path.exists(self.acname)):
                logger.error('Auto correlation file %s does not exist',self.acname)
                return None
        command+=' -o %s' % (uvfitsname)
        if (self.flag):
            command+=' -f'
            # allow for new flagging modes
            # 2011-07 version of corr2uvfits
            if (self.correlator == "S"):
                command+=' 1'
            else:
                command+=' 2'
        if (self.flagfile is not None and len(self.flagfile)>0):
            if not os.path.exists(self.flagfile):
                logger.error('corr2uvfits global flag file %s does not exist',self.flagfile)
                return None
            else:
                command+=' -F %s' % self.flagfile
        command+=' -S %s' % self.antenna_locations
        command+=' -I %s' % self.instr_config
        command+=' -H %s' % self.headername
        if (not os.path.exists(uvfitsname) or self.force):
            if (os.path.exists(uvfitsname)):
                logger.info('UVFITS file %s exists but force==True' % (uvfitsname))
            result=runit(command,fake=fake)
            if (hasstring(result[1],'ERROR')):
                logger.error('Error running corr2uvfits:\n\t%s',''.join(result[1]))
                return None
        else:
            logger.info('UVFITS file %s exists: not overwriting',uvfitsname) 
        try:
            f=pyfits.open(uvfitsname,'update')
        except IOError,err:
            logger.error('Cannot open UVFits file %s\n%s', uvfitsname,err)
            return None
        f.verify('fix')
        try:
            h=f[0].header
            h.update('UVFITSRV',self.revision,'Revision number of UVFITS converter')
            h.update('N_INPUTS',self.n_inputs,'Number of inputs')
            h.update('N_CHANS',self.n_chans,'Number of channels')
            h.update('BANDWDTH',self.bandwidth,'[MHz] Total bandwidth')
            h.update('INV_FREQ',ternary(self.invert_freq,pyfits.TRUE,pyfits.FALSE),'Invert frequencies?')
            h.update('CONJGATE',ternary(self.conjugate,pyfits.TRUE,pyfits.FALSE),'Conjugate inputs?')
            h.update('INTTIME',self.inttime,'[s] Time of each integrations')
            h.update('EXPTIME',self.totaltime,'[s] Total time of observation')
            h.update('INSTCONF',self.instr_config,'Instrument configuration file')
            h.update('ANTENNAS',self.antenna_locations,'Antenna locations file')
            h.update('HA_HRS',self.HA,'[hrs] Hour Angle')
            h.update('LST_HRS',self.lst,'[hrs] Local sidereal time')
            h.update('FREQCENT',channel2frequency(int(self.channel)),'[MHz] Center frequency for full band')
            # DLK
            # cannot update DATE-OBS here - leave it as miriad likes it
            h.update('OBSNDATE','%4d-%02d-%02dT%s'
                     % (int(self.year),int(self.month),int(self.day),self.time),'Date of observation')
            #t=self.time[0:2] + 'h' + self.time[3:5] + 'm' + self.time[6:] + 's' 
            if (self.ccname):
                h.update('CCNAME',self.ccname,'Name of CC file')
            if (self.acname):
                h.update('ACNAME',self.acname,'Name of AC file')
            h.update('CORRTYPE',self.corrtype,'Correlation type. C(ross), B(oth), or A(uto)')
            h.update('CORRFLAG',ternary(self.flag,pyfits.TRUE,pyfits.FALSE),
                     'Flagging done during conversion to UVFITS?')
            if (self.flagfile is not None):
                h.update('CORRFILE',self.flagfile,
                         'Global flagging file');
            else:
                h.update('CORRFILE','NONE',
                         'Global flagging file');
            f.flush(output_verify='fix')

            # need this for some reason to update the header cards
            # they were made lowercase, which miriad cannot read
            # I tried to fix this purely in pyfits
            # but that screwed up the ordering
            f3=open(uvfitsname,'ra+')
            n=0
            while n < 36*2:
                s=f3.read(80)
                n+=1
                if ('PTYPE' in s):
                    s=s.upper()
                    f3.seek(f3.tell()-80)
                    f3.write(s)
            f3.flush()
                

        except:
            logger.error('Error updating FITS header for %s:\n%s',
                          uvfitsname,sys.exc_info()[1])
            return 0

        return uvfitsname
######################################################################
# Utility functions
######################################################################

######################################################################
def runit(command,stdin=None,fake=0,verbose=1, **kwargs):
    """
    stdout,stderr=runit(command,stdin=None,fake=0,verbose=1)
    wraps os.system() to log results (using logger())
    or will just print statements (if fake==1)
    if (not verbose), will not print
    returns results of stdout and stderr
    """

    try:
        logger.debug(command)
    except NameError:
        pass
    if (verbose):
        print command
    if (not fake):
        try:
            if (stdin is None):
                p=subprocess.Popen(command,shell=True,stderr=subprocess.PIPE,
                                   stdout=subprocess.PIPE, close_fds=True, **kwargs)
                (result,result_error)=p.communicate()
            else:                
                p=subprocess.Popen(command,shell=True,stdin=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   stdout=subprocess.PIPE, close_fds=True, **kwargs)
                (result,result_error)=p.communicate(stdin)
        except:            
            logger.error('Error running command:\n\t%s\n%s', command,sys.exc_info()[1])
            return None
        # go from a single string to a list of strings (one per line)
        if (result is not None):
            result=result.split('\n')
        if (result_error is not None):
            result_error=result_error.split('\n')
        return result,result_error
    return None

######################################################################
def get_instr_config(gpstime, instr_config):

    try:
        fin=open(instr_config, 'r')
    except:
        logger.error('Unable to open master instrument config %s' % (instr_config))
        return None
    lines=fin.readlines()
    outlines=''
    (xdir,xname)=os.path.split(sys.argv[0])
    outlines+='# corr2uvfits header written by %s\n' % (xname)
    now=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    outlines+='# %s\n' % now

    iscommentblock=False
    file_gpstime=None
    config_data={}
    for line in lines:
        if (line.startswith('##############################')):
            if (iscommentblock):
                iscommentblock=False
            else:
                iscommentblock=True

        if (line.startswith('#') and not iscommentblock):
            continue
        elif (line.startswith('#') and iscommentblock):
            outlines+=line
        elif line.lower().startswith('date'):
            try:
                datetimestring=line.split('=')[1].rstrip().lstrip()
                year=int(datetimestring[:4])
                month=int(datetimestring[4:6])
                day=int(datetimestring[6:8])
                hour=int(datetimestring[8:10])
                minute=int(datetimestring[10:12])
                second=int(datetimestring[12:14])
                file_gpstime=int(dateobs2gps('%04d-%02d-%02dT%02d:%02d:%02d' %
                                             (year,month,day,hour,minute,second)))
                config_data[file_gpstime]='# Data starting at %04d-%02d-%02dT%02d:%02d:%02d\n' % (
                    year,month,day,hour,minute,second)
                config_data[file_gpstime]+='# GPS time %d\n' % file_gpstime
            except:
                logger.error('Unable to parse datetimestring\n%s' % line)
                return None
            continue
        else:
            if (file_gpstime is not None):
                config_data[file_gpstime]+=line
    s=sorted(config_data.keys())
    itouse=bisect.bisect_right(s,gpstime)-1
    if (itouse<0):
        logger.error('Cannot find a configuration to match gpstime %d' % gpstime)
        return None
    gpstimetouse=s[itouse]
    outlines+='# For GPS time %d\n' % gpstime
    outlines+=config_data[gpstimetouse]
    return outlines

                
    

######################################################################
def ct2lst_mwa(yr,mn,dy,UT):
    """
    LST=ct2lst_mwa(yr,mn,dy,UT)
    convert from local time to LST (in hours)
    give yr,mn,dy,UT of time to convert
    assumes MWA site
    """
    mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
    observer=ephem.Observer()
    observer.long=mwa.long/ephem_utils.DEG_IN_RADIAN
    observer.lat=mwa.lat/ephem_utils.DEG_IN_RADIAN
    observer.elevation=mwa.elev
    s=str(UT)
    if (s.count(':')>0):
        # it's hh:mm:ss
        # so leave it
        UTs=UT
    else:
        UTs=ephem_utils.dec2sexstring(UT,digits=0,roundseconds=0)
    observer.date='%d/%d/%d %s' % (yr,mn,dy,UTs)
    lst=observer.sidereal_time()*ephem_utils.HRS_IN_RADIAN
    return lst
######################################################################
def sundistance(RA, Dec, yr,mn,dy,UT):
    """
    distance=sundistance(RA, Dec, yr,mn,dy,UT)
    input position is in degrees
    result is in degrees
    returns the distance between the Sun and the specified position at the specified time
    """
    ra,dec,az,alt=sunposition(yr,mn,dy,UT)
    distance=ephem_utils.angulardistance(RA/15.0,Dec,ra/15.0,dec)*ephem_utils.DEG_IN_RADIAN
    return distance

######################################################################
def sunposition(yr,mn,dy,UT):
    """
    ra,dec,az,alt=sunposition(yr,mn,dy,UT)
    all returned values are in degrees
    """
    mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
    observer=ephem.Observer()
    observer.long=mwa.long/ephem_utils.DEG_IN_RADIAN
    observer.lat=mwa.lat/ephem_utils.DEG_IN_RADIAN
    observer.elevation=mwa.elev
    s=str(UT)
    if (s.count(':')>0):
        # it's hh:mm:ss
        # so leave it
        UTs=UT
    else:
        UTs=ephem_utils.dec2sexstring(UT,digits=0,roundseconds=0)
    observer.date='%d/%d/%d %s' % (yr,mn,dy,UTs)
    sun=ephem.Sun()
    sun.compute(observer)
    az=sun.az*ephem_utils.DEG_IN_RADIAN
    alt=sun.alt*ephem_utils.DEG_IN_RADIAN
    ra=sun.ra*ephem_utils.DEG_IN_RADIAN
    dec=sun.dec*ephem_utils.DEG_IN_RADIAN

    return (ra,dec,az,alt)
######################################################################
def channel2frequency(channel):
    """
    returns center frequency (in MHz) given a channel
    """
    return 1.28*channel-0.625
######################################################################
def dateobs2gps(dateobs):
    """ takes a FITS date-obs string
    YYYY-MM-DDThh:mm:ss
    and converts to gps seconds
    """
    date,ut=dateobs.split('T')
    yr,mn,dy=date.split('-')
    hour,min,sec=ut.split(':')
    UT=float(hour)+float(min)/60.0+float(sec)/3600.0    
    MJD=ephem_utils.cal_mjd(int(yr),int(mn),int(dy))
    
    gps=ephem_utils.calcGPSseconds(MJD,UT)
    return gps

######################################################################
def parse_boolinput(inp):
    ret=None
    try:
        # if it is an int(), like 1 or 0
        ret=bool(int(inp))
    except ValueError:
        if (inp.upper in ('F','FALSE')):
            ret=False
        if (inp.upper in ('T','TRUE')):        
            ret=True
    return ret
######################################################################
def ternary(condition, value1, value2):
    """
    python 2.4 does not have a ternary operator
    so redo it here
    """
    if (condition):
        return value1
    else:
        return value2
######################################################################
def parse_RA(s):
    """
    s=parse_RA(s)
    will accept RA in either HH:MM:SS or DDD.ddd
    and return HH:MM:SS
    """
    if (s.count(':')>0):
        #return trim_string(s)
        return string.strip(s)
    else:
        return ephem_utils.dec2sexstring(float(s)/15,digits=1,roundseconds=0)
    
######################################################################
def parse_Dec(s):
    """
    s=parse_Dec(s)
    will accept Dec in either sDD:MM:SS.ss or sDDD.ddd
    and return sDD:MM:SS.ss
    """
    if (s.count(':')>0):
#        return trim_string(s)
        return string.strip(s)
    else:
        return ephem_utils.dec2sexstring(float(s),digits=1,roundseconds=0)
######################################################################
def hasstring(S,s):
    """
    result=hasstring(S,s)
    returns True if string s is in any element of list S
    """
    try:
        return any([s in S[i] for i in xrange(len(S))])
    except NameError:
        # put this in for python 2.4 which does not have any()
        return sum([s in S[i] for i in xrange(len(S))])>=1

######################################################################

if __name__=="__main__":
    main()
