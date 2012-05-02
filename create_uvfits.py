"""
create_uvfits.py

standalone program to create UVFITS files for MWA 32T data
based on elements of image_32T.py
can operate from:
 individual das output files
 splatted correlator output
 averaged correlator output


uses class:
Corr2UVFITS
takes software correlator output
converts to uvfits
needs various metadata to get the times/positions right

"""


import getopt,sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob
import ephem
import pyfits
from mwapy import ephem_utils
import numpy

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('create_uvfits')
logger.setLevel(logging.INFO)

######################################################################
# external routines
# the value after is 1 (if critical) or 0 (if optional)
external_programs={'corr2uvfits': 1,
                   'splatdas': 0,
                   'average_corr.py': 0}
                   
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
def usage():
    (xdir,xname)=os.path.split(sys.argv[0])
    print "Usage:"
    print "\t%s\t[--force=0/1] [--autoflag=0/1] [--instr=<instrument_config>] [--antenna=<antenna_locations>] [--flag=<flagfile>] [--inttime=<integration_time>] [--ra=<RA>] [--dec=<Dec>] [--timeoffset=<timeoffset>] [--conjugate=0/1] [--correlator=H/S] [--object=<object>] <directory> [<directory2> ...]\n" % xname
    print "\t\tSpecify directories to process.  Each should contain correlator output with one of:\n\t\t\t<directory>/<directory>_das1.lacspc (etc)"
    print "\t\t\t<directory>/<directory>.lacspc"
    print "\t\t\t<directory>/<directory>.av.lacspc"
    print "\t\tWill generate <directory>/<directory>.uvfits\n"
    print "\t\tRequires external programs %s for operation; searches $MWA_PATH for these\n" % (", ".join(external_programs.keys()))
    print "\t\t--help\t\t\t\tReturn usage information"
    print "\t\t--debug\t\t\t\tTurn on debug-level outout"
    print "\t\t--force=0/1\t\t\tForce regeneration of files"
    print "\t\t--autoflag=0/1\t\t\tUse autoflagging in corr2uvfits? (default=True)"
    print "\t\t--instr=<instrument_config>\tSpecify the instrument configuration file (default=instr_config.txt)"
    print "\t\t--antenna=<antenna_locations>\tSpecify the antenna locations file (default=antenna_locations.txt)"
    print "\t\t--flag=<flagfile>\t\tSpecify a static masking file for the channels"
    print "\t\t--inttime=<integration_time>\tSpecify integration time in seconds; >1 indicates averaging"
    print "\t\t--ra=<RA>\t\t\tPhase center RA (decimal degrees or HH:MM:SS) (default=meridian)"
    print "\t\t--dec=<Dec>\t\t\tPhase center Dec (decimal degrees or DD:MM:SS) (default=zenith)"    
    print "\t\t--timeoffset=<timeoffset>\tSpecify time offset in seconds between the file datetime and the observation starttime (default=2)"
    print "\t\t--conjugate=0/1\t\t\tConjugate correlator input (default=True)"
    print "\t\t--correlator=H/S\t\tSpecify hardware (H) or software (S) correlator (default=H)"
    print "\t\t--object=<object>\t\tSpecify object name"

    
    

        
######################################################################
def main():
    roots=[]
    autoflag=True
    cwd=os.path.abspath(os.getcwd()) + '/'
    instrument_config=cwd + "instr_config.txt"
    antenna_locations=cwd + "antenna_locations.txt"
    static_flag=None
    force=False
    inttime=1
    ra=None
    dec=None
    timeoffset=2
    conjugate=True
    correlator='H'
    objectname=None

    try:
        opts, args = getopt.getopt(sys.argv[1:], 
                     "h",
                    ["help",
                     "debug",
                     "autoflag=",
                     "instr=",
                     "antenna=",
                     "flag=",
                     "force=",
                     "inttime=",
                     "ra=",
                     "RA=",
                     "dec=",
                     "DEC=",
                     "timeoffset=",
                     "conjugate=",
                     "correlator=",
                     "object="
                     ])
    except getopt.GetoptError,err:
        logger.error('Unable to parse command-line options: %s\n',err)
        usage()
        sys.exit(2)

    for opt,val in opts:
        # Usage info only
        if opt in ("-h", "--help"):
            usage()
            sys.exit(1)
        elif opt in ("--debug"):
            logger.setLevel(logging.DEBUG)
        elif opt in ("--ra","--RA"):
            ra=parse_RA(val)
        elif opt in ("--dec","--DEC"):
            dec=parse_Dec(val)
        elif opt in ("--autoflag"):
            autoflag=parse_boolinput(val)
        elif opt in ("--force"):
            force=parse_boolinput(val)
        elif opt in ("--conjugate"):
            conjugate=parse_boolinput(val)
        elif opt in ("--correlator"):
            correlator=val
        elif opt in ("--object"):
            objectname=val
        elif opt in ("--inttime"):
            try:
                inttime=int(val)
            except ValueError,err:
                logger.warning('Unable to parse option  --inttime=%s: %s', val,err)
        elif opt in ("--timeoffset"):
            try:
                timeoffset=int(val)
            except ValueError,err:
                logger.warning('Unable to parse option  --timeoffset=%s: %s', val,err)
        elif opt in ("--antenna"):
            if ("/" in val):
                antenna_locations=val
            else:
                antenna_locations=cwd + val
            if not os.path.exists(antenna_locations):
                logger.error('Unable to find antenna_locations file %s' % antenna_locations)
                sys.exit(2)
        elif opt in ("--instr"):
            if ("/" in val):
                instrument_config=val
            else:
                instrument_config=cwd + val
            if not os.path.exists(instrument_config):
                logger.error('Unable to find instrument_config file %s' % instrument_config)
                sys.exit(2)
        elif opt in ("--flag"):
            if ("/" in val):
                static_flag=val
            else:
                static_flag=cwd + val
            if not os.path.exists(static_flag):
                logger.error('Unable to find static_flag file %s' % static_flag)
                sys.exit(2)
                
        else:
            logger.warning('Unknown option %s', opt)

    roots=args
    for root in roots:
        uvfitsname=None
        logger.info('# Moving to %s' % root)
        basedir=root
        if ("." in basedir):
            basedir=basedir.split(".")[0]
        if (not os.path.exists(basedir)):
            logger.error('Directory %s does not exist',basedir)
            return None
        try:
            os.chdir(basedir)
        except OSError,err:
            logger.error('Unable to change directory to: %s\n%s',basedir,err)

        corr2uvfits=Corr2UVFITS(basename=root,RA=ra,Dec=dec,
                                objectname=objectname,inttime=inttime,
                                flag=autoflag,
                                flagfile=static_flag,
                                instr_config=instrument_config, antenna_locations=antenna_locations,
                                conjugate=conjugate,correlator=correlator,timeoffset=timeoffset,force=force,
                                fake=False)
        if (not corr2uvfits.write_header_file()):
            logger.error('Error in writing header file')
            os.chdir('../')
            return None
        uvfitsname=corr2uvfits.write_uvfits()
        if (not uvfitsname):
            logger.error('Error in writing UVFITS file')
            os.chdir('../')
            return None
        logger.info('%s/%s written!' % (basedir,uvfitsname))
        os.chdir('../')                

                
            
##################################################
class Corr2UVFITS:
##################################################
    """ A class to convert 32T correlator output to UVFITS files
    """

    ##################################################
    def __init__(self,basename=None,objectname=None,RA=None,Dec=None,inttime=1,totaltime=None,flag=0,flagfile=None,antenna_locations=None,instr_config=None,conjugate=0,correlator='s',timeoffset=2,force=False,fake=None):
        """
        __init__(self,basename=None,objectname=None,RA=None,Dec=None,inttime=1,totaltime=None,flag=0,
        flagfile=None,antenna_locations=None,instr_config=None,conjugate=0,correlator='s',timeoffset=2,force=False,
        fake=None)
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
    
        # first step: corr2uvfits
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

        # processing steps
        self.basename_processed=0
        self.has_headerfile=0

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
            if (not (os.path.exists(self.basename + suffix + '.lccspc') or os.path.exists(self.basename + suffix + '.LCCSPC')) or self.force):
                # do splatdas if necessary to create basic auto and cross correlation files
                if (not (os.path.exists(self.basename + '.lccspc') or os.path.exists(self.basename + '.LCCSPC')) or self.force):
                    if ((os.path.exists(self.basename + '.lccspc'))):
                        logger.info('splated file %s exists but force==True' % (self.basename + '.lccspc'))
                    if ((os.path.exists(self.basename + '.LCCSPC'))):
                        logger.info('splated file %s exists but force==True' % (self.basename + '.LCCSPC'))
                    
                    if (os.path.exists(self.basename + '_das1.LACSPC') or os.path.exists(self.basename + '_das1.LCCSPC')):
                        # need to do splatdas first
                        [datetime_str,self.year,self.month,self.day,time,self.channel]=self.parse_basename()
                        command='%s -c %d -o %s -1 %s_das1 -2 %s_das2 -3 %s_das3 -4 %s_das4' % (
                            external_paths['splatdas'],self.channel,self.basename,
                            self.basename,self.basename,self.basename,self.basename)
                        logger.info('Running splatdas...\n')
                        result=runit(command,fake=self.fake)
                        if (hasstring(result[1],'Error')):
                            logger.error('Error running splatdas:\n\t%s',''.join(result[1]))
                            return None
                    else:
                        logger.error('Cannot find das1 file %s or %s' % (
                                self.basename + '_das1.LACSPC',self.basename + '_das1.lacspc'))
                        return None
                # do average_corr.py if necessary
                if (self.inttime > 1 and (not (os.path.exists(self.basename + suffix + '.lccspc') or os.path.exists(self.basename + suffix + '.LCCSPC')) or self.force)):
                    if ((os.path.exists(self.basename + suffix + '.lccspc'))):
                        logger.info('averaged file %s exists but force==True' % (self.basename + suffix + '.lccspc'))
                    if ((os.path.exists(self.basename + suffix + '.LCCSPC'))):
                        logger.info('averaged file %s exists but force==True' % (self.basename + suffix + '.LCCSPC'))

                    command='%s -a %d %s' % (external_paths['average_corr.py'],self.inttime,self.basename)
                    logger.info('Running average_corr.py...\n')
                    result=runit(command,fake=self.fake)
                    if (hasstring(result[1],'Error')):
                        logger.error('Error running average_corr.py:\n\t%s',''.join(result[1]))
                        return None
                    

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
            [datetime_str,self.year,self.month,self.day,time,self.channel]=self.parse_basename()
            try:
                self.datetime=datetime.datetime(self.year,self.month,self.day,int(time[0:2]),int(time[2:4]),int(time[4:6]))+datetime.timedelta(seconds=self.timeoffset)
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
                logger.warning('Sun is %.1f degrees away from the field',sundist)

            if (self.conjugate):
                logger.warning('Conjugating correlator input')

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
            logger.info('# Header file written to %s' %  outputname)
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
        antenna_dir=os.path.abspath(os.path.dirname(self.antenna_locations))
        instr_dir=os.path.abspath(os.path.dirname(self.instr_config))

        if not (curpath + '/antenna_locations.txt' == antenna_dir + '/' + self.antenna_locations):
            if (os.path.exists('antenna_locations.txt')):
                os.remove('antenna_locations.txt')
            shutil.copyfile(self.antenna_locations,'antenna_locations.txt')
        if not (curpath + '/instr_config.txt' == instr_dir + '/' + self.instr_config):
            if (os.path.exists('instr_config.txt')):
                os.remove('instr_config.txt')
            shutil.copyfile(self.instr_config,'instr_config.txt')
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
        return trim_string(s)
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
        return trim_string(s)
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
