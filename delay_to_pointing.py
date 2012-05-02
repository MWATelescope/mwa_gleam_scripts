import getopt,sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob
import ephem
import pyfits
from mwapy import ephem_utils
import numpy

######################################################################
class gridPointing():
    
    def __init__(self, name, az, el, delays):
        """
        __init__(self, name, az, el, delays)
        az,el in decimal degrees
        """
        self.name=name
        self.az=az
        self.el=el
        self.delays=delays

    def radec(self, datetime):
        """
        RA,Dec=radec(self, datetime)
        returns decimal degrees
        """
        try:
            year=int(datetime[:4])
            month=int(datetime[4:6])
            day=int(datetime[6:8])
            time=datetime[8:10] + ':' + datetime[10:12] + ':' + datetime[12:]
        except:
            return None
        lst=ct2lst_mwa((year),(month),(day),time)
        mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
        [HA,Dec]=ephem_utils.horz2eq(self.az,self.el,mwa.lat)
        RA=lst*15-HA
        while (RA<0):
            RA+=360
        while (RA>=360):
            RA-=360
        return RA,Dec

######################################################################
def main():

    datetime=None
    delays_tomatch=[]
    try:
        opts, args = getopt.getopt(sys.argv[1:], 
                                   "h",
                                   ["help",
                                    "datetime=",
                                    "delays="]
                                   )
    except getopt.GetoptError,err:
        sys.stderr.write('Unable to parse command-line options: %s\n',err)
        usage()
        sys.exit(2)

    for opt,val in opts:
        # Usage info only
        if opt in ("-h", "--help"):
            usage()
            sys.exit(1)
        elif opt in ("--datetime"):
            datetime=val
        elif opt in ("--delays"):
            try:
                if (',' in val):
                    delays_tomatch=map(int,val.split(','))
                else:
                    delays_tomatch=16*[int(val)]
            except:
                sys.stderr.write("Could not parse beamformer delays %s\n" % val)
                sys.exit(1)

    if datetime is None:
       sys.stderr.write('Must give a datetime string with the form YYYYMMDDhhmmss')
       sys.exit(1)
    if (delays_tomatch is None or len(delays_tomatch)<16):
       sys.stderr.write('Must supply a set of 16 beamformer delays')
       sys.exit(1)


    # get the list of pointing delay positions
    dir=os.path.dirname(__file__)
    if (len(dir)==0):
        dir='.'
    grid_database=dir + '/' + 'grid_points.dat'

    if not os.path.exists(grid_database):
        sys.stderr.write('Cannot open grid database %s' % grid_database)
        sys.exit(2)
    f=open(grid_database,'r')
    lines=f.readlines()
    grid_pointings=[]
    for line in lines:
        if (line.startswith('#')):
            continue
        d=line.split('|')
        s=d[-1]
        delays=[int(x) for x in (s.replace('{','').replace('}','')).split(',')]
        name=d[0] + d[1]
        grid_pointings.append(gridPointing(name, float(d[2]), float(d[3]), delays))

    for grid_pointing in grid_pointings:
        if (grid_pointing.delays == delays_tomatch):
            try:
                ra,dec=grid_pointing.radec(datetime)
            except:
                sys.stderr.write('Unable to determine RA,Dec from pointing information')
                sys.exit(1)
            print "Delay=%s at %s: (Az,El)=(%.5f, %.5f), (RA,Dec)=(%.5f, %.5f)" % (delays_tomatch,datetime,grid_pointing.az,grid_pointing.el,ra,dec)
            return
    print "Did not find a matching delay pointing for %s" % delays_tomatch


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
def usage():
    (xdir,xname)=os.path.split(sys.argv[0])
    print "Usage:"
    print "\t%s\t--datetime=<datetime> --delays=<delays>\n" % xname
    print "<datetime> should be of the form YYYYMMDDhhmmss"
    print "<delays> should be 16 integers separated by commas"
    print "Example:\tpython ~/mwa/MWA_Tools/delay_to_pointing.py --datetime=20110927154959 --delays=12,8,4,0,12,8,4,0,12,8,4,0,12,8,4,0\n"

    

######################################################################
# Running as executable
if __name__=='__main__':
    main()
    
