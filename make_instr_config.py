"""
generates an instrument configuration
maps input number into antenna/polarization
also includes electrical length and whether or not to flag the input

Usage:

gpstime=1001175315
flaggingname=None
T=instrument_configuration(gpstime=gpstime, db=db)
T.make_instr_config(flaggingname=flaggingname)
print T
"""


import sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob
import itertools
from optparse import OptionParser,OptionGroup
import ephem
import pyfits
from mwapy import ephem_utils, dbobj
    
import splat_average, get_observation_info
import numpy


# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('make_instr_config')
logger.setLevel(logging.INFO)

try:
    from obssched.base import schedule
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)

# open up database connection
try:
    db = schedule.getdb()
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)

# 32 antennas * 2 polns
_NINP=64
# 16 inputs (16 antennas * 2 polns) go into each Rx
_INPUTSPERRX=16

######################################################################
class tile_config():
    """
    class tile_config()
    holds configuration information for a single tile/polarization:

    recevier number
    slot number
    input number
    polarization
    length (electrical + physical)
    flag status

    this can be used to generate an instr_config file
    """
    
    ##################################################    
    def __init__(self, tile=None, receiver=None, slot=None, inputnumber=None, pol=None, length=None, flag=False):
        self.tile=tile
        self.receiver=receiver
        self.slot=slot
        self.inputnumber=inputnumber
        self.pol=pol
        self.length=length
        self.flag=flag

    ##################################################    
    def __str__(self):
        if (self.flag):
            f=1
        else:
            f=0
        s="%d\t%d\t%s\t%.2f\t%d" % (self.inputnumber, int(self.tile)-1, self.pol.upper(), self.length, f)
        return s

######################################################################
class instrument_configuration():
    """
    generates an instrument configuration
    maps input number into antenna/polarization
    also includes electrical length and whether or not to flag the input

    Usage:

    gpstime=1001175315
    flaggingname=None
    T=instrument_configuration(gpstime=gpstime, db=db)
    T.make_instr_config(flaggingname=flaggingname)
    print T
    """


    ##################################################    
    def __init__(self, gpstime=None, db=None):
        self.inputs={}
        self.db=db        
        self.tiles_to_flag=set([])
        self.gpstime=gpstime

        # this is the mapping from input number to slot number
        self._inptoslot={0:4,1:4,
                         2:3,3:3,
                         4:2,5:2,
                         6:1,7:1,
                         8:8,9:8,
                         10:7,11:7,
                         12:6,13:6,
                         14:5,15:5}
        # and the mapping from input number to polarization
        self._inptopol={0:'Y',1:'X',
                        2:'Y',3:'X',
                        4:'Y',5:'X',
                        6:'Y',7:'X',
                        8:'Y',9:'X',
                        10:'Y',11:'X',
                        12:'Y',13:'X',
                        14:'Y',15:'X'}
    ##################################################    
    def __str__(self):
        preamble="""##################################################
# this file maps inputs into the receiver/correlator to antennas and polarisations.
# in addition, a cable length delta (in meters) can be specified
# the first column is not actually used by the uvfits writer, but is there as
# an aide to human readers. Inputs are ordered from 0 to n_inp-1
# antenna numbering starts at 0
# lines beginning with '\#' and blank lines are ignored. Do not leave spaces in empty lines.
#
# Input flagging: put a 1 in the flag column to flag all data from that input.
#                 0 means no flag.
"""
        s=preamble
        s+='# Written by %s\n' % (__file__.split('/')[-1])        
        now=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        s+='# %s\n' % now
        s+="""##################################################
# INPUT   ANTENNA   POL     DELTA   FLAG 
"""
        for inputnumber in sorted(self.inputs.keys()):
            s+='%s\n' % (self.inputs[inputnumber])
        return s


    ##################################################    
    def get_tiles_to_flag(self, flaggingname=None):
        if (self.db is None):
            logger.error('Cannot retrieve flagging information without database connection')
            return
        if (flaggingname is not None):    
            flagged_tiles = dbobj.execute('select flagged_tiles from tile_flags where starttime < %d and stoptime > %d and name = %s' %
                                          (self.gpstime, self.gpstime, flaggingname), db=self.db)    
        else:
            flagged_tiles = list(itertools.chain.from_iterable(dbobj.execute('select flagged_tiles from tile_flags where starttime < %d and stoptime > %d' %
                                                                             (self.gpstime, self.gpstime), db=self.db)))
    
        # logical or of all of the flagging sets that are returned
        for x in flagged_tiles:
            for z in x.replace('{','').replace('}','').split(','):
                self.tiles_to_flag.add(z)
        logger.info('Will flag tiles %s' % list(self.tiles_to_flag))


    ##################################################    
    def make_instr_config(self, flaggingname=None):
        """
        based on a recipe from Bryna Hazelton
        2012-05
        """
        if (self.gpstime is None):
            logger.error('Must supply gpstime for determining instr_config')
            return

        if (self.db is None):
            logger.error('Cannot retrieve configuration information without database connection')
            return

        self.get_tiles_to_flag(flaggingname=flaggingname)
        
        # figure out which receivers are active
        active_receivers = dbobj.execute('select receiver_id from receiver_info where active = true and begintime < %d and endtime > %d' % (self.gpstime,self.gpstime), db=self.db)
        self.active_receivers = [x[0] for x in active_receivers]
        logger.info('Found active receivers %s' % self.active_receivers)
        if len(self.active_receivers)<1:
            logger.error('No active receivers found for gpstime=%d' % self.gpstime)
            return

        if 102 in self.active_receivers:
            # the offset for mapping from each Rx to the slot numbers
            rxslotoffset={1:0,102:16,3:32,4:48}
        else:
            rxslotoffset={1:0,2:16,3:32,4:48}

        # loop over each input 
        # figure out which receiver and tile it connects to
        for inputnumber in xrange(_NINP):
            for receiver in rxslotoffset.keys():
                # get the offset
                if rxslotoffset[receiver]==(inputnumber / _INPUTSPERRX)*_INPUTSPERRX:
                    break
            slotoffset=rxslotoffset[receiver]
            slot=self._inptoslot[inputnumber-slotoffset]
            pol=self._inptopol[inputnumber-slotoffset]
            tile=dbobj.execute('select tile from tile_connection where receiver_id = %s and receiver_slot = %d and begintime < %d and endtime > %d' % (
                    receiver,slot,self.gpstime,self.gpstime), db=self.db)[0][0]
            cable_electrical_length=dbobj.execute('select eleclength from cable_info ci inner join tile_connection tc on ci.name = tc.cable_name where tc.tile=%s and ci.begintime < %d and ci.endtime >  %d and tc.begintime <  %d and tc.endtime > %d' % (
                    tile,self.gpstime,self.gpstime,self.gpstime,self.gpstime), db=self.db)[0][0]
            flagthisinput=False
            try:
                slotispowered=dbobj.execute('select slot_power from obsc_recv_cmds where rx_id=%s and starttime=%d' % (
                        receiver,self.gpstime), db=self.db)[0][0]
                # if any of them is False
                if 'f' in slotispowered:
                    flagthisinput=True
            except:
                pass

            if tile in self.tiles_to_flag or str(tile) in self.tiles_to_flag:
                flagthisinput=True

            t=tile_config(tile=tile, receiver=receiver, inputnumber=inputnumber, length=cable_electrical_length,
                          pol=pol.upper(), slot=slot, flag=flagthisinput)
            self.inputs[inputnumber]=t
    


