"""
$Rev: 4142 $:     Revision of last commit
$Author: dkaplan $:  Author of last commit
$Date: 2011-10-31 11:30:40 -0500 (Mon, 31 Oct 2011) $:    Date of last commit

"""

from mwapy import ephem_utils
try:
    from obssched.base import schedule
except:
    pass
import sys,bisect
try:
    from receiverStatusPy import ReceiverStatusParser,StatusTools
    use_statustools=True
except:
    use_statustools=False
import pyfits,numpy,math
import os
import getopt

######################################################################
def main():

    freq=100.0
    useazza=False
    xpol=True
    ypol=True
    HA=None
    Dec=None
    try:
        opts, args = getopt.getopt(sys.argv[1:], 
                                   "hf:c:a:xy",
                                   ["help",
                                    "chan=",
                                    "freq=",
                                    "az=",
                                    "HA=",
                                    "Dec="])
    except getopt.GetoptError,err:
        logger.error('Unable to parse command-line options: %s\n',err)
        usage()
        sys.exit(2)        

    for opt,val in opts:
        # Usage info only
        if opt in ("-h", "--help"):
            usage()
            sys.exit(1)
        elif opt in ("-c","--chan"):
            chan=int(val)
            freq=chan*1.28
        elif opt in ("-f","--freq"):
            freq=float(val)
        elif opt in ("-a","--az"):
            useazza=int(val)
        elif (opt in ("-x")):
            ypol=False
        elif (opt in ("-y")):
            xpol=False
        elif (opt in ("--HA")):
            HA=float(val)
        elif (opt in ("--Dec")):
            Dec=float(val)
        
    if (len(args)>0):
        for datetime in args:
            write_primary_beam(datetime=datetime, freq=freq*1e6, useazza=useazza, xpol=xpol, ypol=ypol,HA=HA,Dec=Dec)
    else:
            write_primary_beam(freq=freq*1e6, useazza=useazza, xpol=xpol, ypol=ypol,HA=HA,Dec=Dec)        
            
######################################################################
# Based on Chris Williams' get_delays.py
# 2010-06-03
######################################################################
def getDelays(gpstime):
    try:
        db=schedule.getdb()
    except NameError:
        logger.error('Cannot use the schedule database; use static database instead (getDelays2)')
        return None
    curs=db.cursor()    
    delays={}

    for rx in (1,2,3,4):
        mask=0
        delays[rx]={}

        while mask & 255 != 255:
            cmd="select rx_id,beamformer_mask,delays,update_time,status from bf_status where update_time <= %f and rx_id=%i and beamformer_mask & %i != beamformer_mask order by update_time desc limit 1"%(gpstime,rx,mask)
            curs.execute(cmd)
            row=curs.fetchone()
            colnames=[t[0] for t in curs.description]
            data=dict(zip(colnames,row))
            mask |= data['beamformer_mask']
            for slot in range(1,9):
                if data['beamformer_mask'] & (1<<(slot-1))==(1<<(slot-1)):
                    if data['status']==1:
                        delays[rx][slot]=[int(a) for a in data['delays'][1:-1].split(',')]
                    else:
                        delays[rx][slot]=None


    mydelay=None
    match=True

    for rx,slots in delays.iteritems():
        for slot,delayset in slots.iteritems():
            if delayset is not None:
                if mydelay is None:
                    mydelay=delayset
                else:
                    if mydelay != delayset:
                        match=False
            else:
                print >>sys.stderr,"Rx %i Slot %i is Off"%(rx,slot)

    if match:
        return mydelay
    else:
        print >>sys.stderr,"No Match!"
        print >>sys.stderr,delays
        return None
'''
    stime=curs.fetchone()[0]
    cmd="select rx_id,beamformer_mask,delays,update_time from bf_status where update_time = %f and status=1"%stime
    curs.execute(cmd)
    rows=curs.fetchall()
    
    colnames=[t[0] for t in curs.description]
    data=[dict(zip(colnames,row)) for row in rows]
    
    for row in data:
        print row['delays'], row['update_time']
'''
    
    
######################################################################
def daystr2gps(daystr):
    """
    gpstime=daystr2gps(daystr)
    returns the gpstime associated with a daystring YYYYMMDDhhmmss
    """
    yr=int(daystr[0:4])
    mn=int(daystr[4:6])
    dy=int(daystr[6:8])

    hour=int(daystr[8:10])
    min=int(daystr[10:12])
    sec=int(daystr[12:14])

    UT=float(hour)+float(min)/60.0+float(sec)/3600.0
    
    MJD=ephem_utils.cal_mjd(yr,mn,dy)

    gps=ephem_utils.calcGPSseconds(MJD,UT)
    return gps

######################################################################
def getKeys(statdict):
    keys={}
    for rx in statdict.keys():
        keys[rx]=[time for time,file in statdict[rx]]
    return keys 

######################################################################
def readStatusTimes(statfile):
    
    statdict={}
    statdict[1]=[]
    statdict[2]=[]
    statdict[3]=[]
    statdict[4]=[]
    # the X16 data have Rx102 instead of 2
    statdict[102]=[]

    r=open(statfile)

    for path in r:
        fname=path.split('/')[-1].rstrip()
        if ('Rx102' in fname):
            rx=int(fname[2:5])
            try:
                gpstime=float(fname[6:])
            except:
                print fname
        else:
            rx=int(fname[2:4])
            try:
                gpstime=float(fname[5:])
            except:
                print fname
        bisect.insort(statdict[rx],(gpstime,path.rstrip()))

    r.close()
    return statdict

######################################################################
def getDelays2(gpstime,verbose=False):
    """ like getDelays, but relies on static local database rather
    than M&C database
    """
    X16=False
    #statdict=readStatusTimes("/r4/clmw/X13/newstatus.list")
    if (gpstime > 953000000 and gpstime < 954000000):
        statdict=readStatusTimes("/data/kaplan/mwadata/MANDC_DATA/RxStatusFiles_X13.list")
    elif (gpstime > 960000000 and gpstime < 970000000):
        statdict=readStatusTimes("/data/kaplan/mwadata/MANDC_DATA/RxStatusFiles_X14.list")
    elif (gpstime > 980000000 and gpstime < 990000000):
        statdict=readStatusTimes("/data/kaplan/mwadata/MANDC_DATA/RxStatusFiles_X15.list")
    elif (gpstime > 1000598415 and gpstime < 1001203215):
        X16=True
        statdict=readStatusTimes("/data/kaplan/mwadata/MANDC_DATA/RxStatusFiles_X16.list")
    else:
        statdict=readStatusTimes("/data/kaplan/mwadata/MANDC_DATA/RxStatusFiles.list")

    keys=getKeys(statdict)

    if (X16):
        rxlist=(1,3,4,102)
    else:
        rxlist=(1,2,3,4)
    
    delays=None
    good=True
    for rx in rxlist:
        index=bisect.bisect_right(keys[rx],gpstime)
        if index==0:
            index=1
        time,file=statdict[rx][index]
        dt=gpstime-time
        if (dt > 3600 or dt < -3600):
            print >>sys.stderr,"Cannot find matching time for %d in Rx Status file: closest match is %d, misses by %d" % (gpstime,time,dt)
            good=False
            return None
        if (verbose):
            print "# Identified file for Rx%d: %s" % (rx,file)
        try:
            myStatus=ReceiverStatusParser.receiverStatus(xmlfile=file)
        except NameError:
            print >>sys.stderr,"Cannot parse xml because Parser is not loaded" 
            good=False
            return None            

        for ID,BF in myStatus.BFs.iteritems(): 

            #xx,yy=StatusTools.decodeDelaySet(BF.DelaySet)
            xx,yy=BF.XDelays,BF.YDelays
            if xx!=yy:
                print >>sys.stderr,"X/Y delays don't match"
                good=False
            else:
                if delays is None:
                    delays=xx
                    templaterx=rx
                    templateBF=BF.ID
                    if verbose:
                        print "# Basing results on Rx,Beamformer=",rx,BF.ID
                        print "# Delays=",delays
                elif delays != xx:
                    print >>sys.stderr,"Different delays on different BFs",delays,xx
                    print >>sys.stderr,"Rx,Beamformer=",rx,BF.ID
                    if (xx is None):
                        xx=delays
                    else:
                        good=False

    return (xx,good)
    #if good or True:
    #    return(xx)
    #else:
    #    return(None)



######################################################################
# Based on code from Daniel Mitchel
# 2012-02-13
# taken from the RTS codebase
######################################################################
def MWA_Tile_analytic(theta, phi, freq=100.0e6, dipheight=0.278, dip_sep=1.1, delays=None, delay_int=435.0e-12, zenithnorm=True):
    """
    gainXX,gainYY=MWA_Tile_analytic(theta, phi, freq=100.0e6, dipheight=0.278, dip_sep=1.1, delays=None, delay_int=435.0e-12, zenithnorm=True)
    gains are voltage gains - should be squared for power
    
    theta is zenith-angle in radians
    phi is azimuth in radians, phi=0 points north
    freq in Hz, height, sep in m
    delays are one per dipole in units of delay_int
    """


    c=2.998e8
    # wavelength in meters
    lam=c/freq

    if (delays is None):
        delays=0

    if (isinstance(delays,float) or isinstance(delays,int)):
        delays=delays*numpy.ones((16))
    if (isinstance(delays,numpy.ndarray) and len(delays)==1):
        delays=delays[0]*numpy.ones((16))        

    # direction cosines (relative to zenith) for direction az,za
    projection_east=numpy.sin(theta)*numpy.sin(phi)
    projection_north=numpy.sin(theta)*numpy.cos(phi)
    projection_z=numpy.cos(theta)

    # dipole position within the tile
    dipole_north=dip_sep*numpy.array([1.5,1.5,1.5,1.5,0.5,0.5,0.5,0.5,-0.5,-0.5,-0.5,-0.5,-1.5,-1.5,-1.5,-1.5])
    dipole_east=dip_sep*numpy.array([-1.5,-0.5,0.5,1.5,-1.5,-0.5,0.5,1.5,-1.5,-0.5,0.5,1.5,-1.5,-0.5,0.5,1.5])
    dipole_z=dip_sep*numpy.zeros(dipole_north.shape)
    
    # loop over dipoles
    array_factor=0.0

    for i in xrange(4):
        for j in xrange(4):
            k=4*j+i
            # relative dipole phase for a source at (theta,phi)
            phase=numpy.exp((1j)*2*math.pi/lam*(dipole_east[k]*projection_east + dipole_north[k]*projection_north +
                                                dipole_z[k]*projection_z-delays[k]*c*delay_int))
            array_factor+=phase/16.0

    ground_plane=2*numpy.sin(2*math.pi*dipheight/lam*numpy.cos(theta))
    # make sure we filter out the bottom hemisphere
    ground_plane*=(theta<=math.pi/2)
    # normalize to zenith
    if (zenithnorm):
        ground_plane/=2*numpy.sin(2*math.pi*dipheight/lam)

    # response of the 2 tile polarizations
    # gains due to forshortening
    dipole_ns=numpy.sqrt(1-projection_north*projection_north)
    dipole_ew=numpy.sqrt(1-projection_east*projection_east)

    # voltage responses of the polarizations from an unpolarized source
    # this is effectively the YY voltage gain
    gain_ns=dipole_ns*ground_plane*array_factor
    # this is effectively the XX voltage gain
    gain_ew=dipole_ew*ground_plane*array_factor

    return gain_ew,gain_ns

######################################################################
# this is now deprecated

# def oldMWA_Tile_analytic(theta, phi, freq=100.0e6, dipheight=0.278, dip_sep=1.1, delays=None, dip_gains=None, delay_int=435.0e-12, xpol=False):
#     """
#     tile_response=MWA_Tile_analytic(theta, phi, freq=100.0e6, dipheight=0.278, dip_sep=1.1, delays=None, dip_gains=None, delay_int=435.0e-12, xpol=False)
#     returns complex voltage(?) response for a tile consisting of 16 short_dipole()
#     freq in Hz, height, sep in m
#     delays are one per dipole in units of delay_int
#     gains are one per dipole
#     can do either xpol or ypol
#     """

#     daz=90
#     if (not xpol):
#         daz=0

#     dy=dip_sep*numpy.array([1.5,1.5,1.5,1.5,0.5,0.5,0.5,0.5,-0.5,-0.5,-0.5,-0.5,-1.5,-1.5,-1.5,-1.5])
#     dx=dip_sep*numpy.array([-1.5,-0.5,0.5,1.5,-1.5,-0.5,0.5,1.5,-1.5,-0.5,0.5,1.5,-1.5,-0.5,0.5,1.5])

#     if (delays is None):
#         delays=0
#     if (dip_gains is None):
#         dip_gains=1

#     if (isinstance(delays,float) or isinstance(delays,int)):
#         delays=delays*numpy.ones((16))
#     if (isinstance(delays,numpy.ndarray) and len(delays)==1):
#         print delays
#         delays=delays[0]*numpy.ones((16))        
#     if (isinstance(dip_gains,float) or isinstance(dip_gains,int)):
#         dip_gains=dip_gains*numpy.ones((16),dtype=numpy.complex)
        
#     # phase delay in radians at each dipole
#     dphase=2*math.pi*freq*(delay_int*delays)
    

#     stheta=numpy.sin(theta)

#     cphi=numpy.cos(phi)*stheta

#     sphi=numpy.sin(phi)*stheta

#     if (isinstance(theta,numpy.ndarray)):
#         tc=numpy.zeros(theta.shape,dtype=numpy.complex)
#         phasefac=numpy.zeros(theta.shape,dtype=numpy.complex)
#     else:
#         tc=0
#         phasefac=0

#     ff=2*math.pi*freq/2.998e8*numpy.complex(0,1)
        
#     short_dip=short_dipole(theta,phi,freq=freq,daz=daz)
#     for dip in xrange(16):
#         tc=numpy.exp(ff*dy[dip]*cphi+ff*dx[dip]*sphi+-1*numpy.complex(0,1)*dphase[dip])
#         tc=tc*(dip_gains[dip]*short_dip)
#         phasefac=phasefac+tc

#     return phasefac

######################################################################
def maketp(lm=False,oned=False,ntheta=91,nphi=360):
    """
    theta,phi=maketp(lm=False,oned=False,ntheta=91,nphi=360)
    returns grid of theta,phi coordinates
    theta goes from pi/2 to 0
    phi goes from 0 to 2*pi
    default is 2D meshgrid, but if oned=True will just be a one-d array
    if lm=True, will also return l=sin(theta)*cos(phi), m=sin(theta)*sin(phi)
    """

    dtheta=math.pi/2/(ntheta-1)
    dphi=2*math.pi/(nphi-1)
    if (oned):
        theta=numpy.zeros(ntheta*nphi)
        phi=numpy.zeros(ntheta*nphi)    

        c=0
        for i in xrange(ntheta):
            for j in xrange(nphi):
                theta[c]=math.pi/2-i*dtheta
                phi[j]=c*dphi
                c+=1
    else:
        theta1=numpy.arange(ntheta)
        phi1=numpy.arange(nphi)
        theta1=math.pi/2-(theta1*dtheta)
        phi1=phi1*dphi
        [theta,phi]=numpy.meshgrid(theta1,phi1)
        
    if (lm):
        m=numpy.sin(theta)*numpy.cos(phi)
        l=numpy.sin(theta)*numpy.sin(phi)
        return theta, phi, l, m
    else:
        return theta,phi


######################################################################
def plot_response(theta,phi,response,square=True):
    """
    plot_response(theta,phi,response,square=True):
    plots the reponse in 3D
    must have matplotlib etc. installed
    if (square), then plots |response|^2
    else assumes real
    """
    import pylab as p
    import mpl_toolkits.mplot3d.axes3d as p3
    from matplotlib import cm

    if (square):
        r=response*numpy.conj(response)
    else:
        r=response
    x=r*numpy.sin(theta)*numpy.cos(phi)
    y=r*numpy.sin(theta)*numpy.sin(phi)
    z=r*numpy.cos(theta)

    fig=p.figure()
    ax=p3.Axes3D(fig)
    ax.plot_wireframe(x,y,z)
    p.show()

######################################################################
def write_primary_beam(datetime=None,freq=100.0e6,useazza=False,xpol=True,ypol=True,HA=None,Dec=None):

    if (not datetime is None):
        dir="./"
        try:
            gps=daystr2gps(datetime)
        except ValueError:
            if ('/' in datetime):
                dir,datetime=os.path.split(datetime)
            while ('.' in datetime):
                datetime,ext=os.path.splitext(datetime)
            # assume that it has channel in there too
            source,channel,datetime=datetime.split('_')
            freq=1.28e6*int(channel)
            gps=daystr2gps(datetime)
        print >>sys.stderr,"GPS time for that observation is: %f" % gps
        mydelay=getDelays2(gps+16)
        if mydelay is not None:
            print >>sys.stderr,str(mydelay)[1:-1]
        else:
            print "None"
            return None
    else:
        mydelay=[0]

    if (useazza):
        theta,phi=maketp()

    else:
        if (HA is not None and Dec is not None):
            # latitude of the site, in degrees
            latMWA=-26.7033194444444
            Az,Alt=ephem_utils.eq2horz(HA,Dec,latMWA)
            
            # go from altitude to zenith angle
            theta=(90-Alt)*math.pi/180
            phi=Az*math.pi/180
        else:
            nDec=120*8
            nHA=180*8
            dDec=(30.0-(-90.0))/(nDec-1)
            dHA=(90.0-(-90.0))/(nHA-1)
            dec=numpy.arange(-90,30,dDec)
            ha=numpy.arange(-90,90,dHA)
            HA,Dec=numpy.meshgrid(ha,dec)
            # latitude of the site, in degrees
            latMWA=-26.7033194444444
            Az,Alt=ephem_utils.eq2horz(HA,Dec,latMWA)
            
            # go from altitude to zenith angle
            theta=(90-Alt)*math.pi/180
            phi=Az*math.pi/180

    respX,respY=MWA_Tile_analytic(theta,phi,freq=freq,delays=numpy.array(mydelay))
    rX=numpy.real(numpy.conj(respX)*respX)
    rY=numpy.real(numpy.conj(respY)*respY)
    if (xpol and ypol):
        r=rX+rY
        polstring=''
    else:
        if (xpol):
            r=rX
            polstring='X'
        else:
            r=rY
            polstring='Y'

    if (isinstance(r,numpy.float64) or len(r)==1):
        print r
        return

    if (not datetime is None):
        outname='%s/primarybeam%s_%s.fits' % (dir,polstring,datetime)
    else:
        outname='primarybeam%s_zenith.fits' % polstring
    if (os.path.exists(outname)):
        os.remove(outname)

    h=pyfits.PrimaryHDU()
    h.data=r
    if (useazza):
        h.header.update('CTYPE1','THETA')
        h.header.update('CRPIX1',1.0)
        h.header.update('CRVAL1',90)
        h.header.update('CDELT1',(180.0/math.pi)*(theta[0,1]-theta[0,0]))
        h.header.update('CTYPE2','PHI')
        h.header.update('CRPIX2',1.0)
        h.header.update('CRVAL2',0)
        h.header.update('CDELT2',(180.0/math.pi)*(phi[1,0]-phi[0,0]))
    else:
        h.header.update('CTYPE1','HA')
        h.header.update('CRPIX1',1.0)
        h.header.update('CRVAL1',-90)
        h.header.update('CDELT1',dHA)
        h.header.update('CTYPE2','DEC')
        h.header.update('CRPIX2',1.0)
        h.header.update('CRVAL2',-90)
        h.header.update('CDELT2',dDec)
        
    if (not datetime is None):
        h.header.update('DATETIME',datetime,'DATETIME string')
        h.header.update('GPSTIME',gps,'GPS time')
        h.header.update('DELAYS',"%s" % mydelay,'Rx delays')
    else:
        h.header.update('DELAYS',"%s" % 'zenith','Rx delays')        
    h.header.update('FREQNCY', (freq/1e6),'[MHz] Frequency')
    h.writeto(outname)
    print >>sys.stderr,"Wrote output to %s" % outname



######################################################################
def usage():
    (xdir,xname)=os.path.split(sys.argv[0])
    print "Usage:"
    print "\t%s [-c/--chan=<channel>] [-f/--freq=<freq>] [-a/--az=<useazel>] [--HA=<HA>] [--Dec=<Dec>] <root(s)>" % xname
    print "\t%s\t[-h/--help]" % xname
    print "\tSpecify frequency or coarse channel"
    print "\tDefault output is in (HA,Dec): if <useazel> is 1, then will do (Az,El)"
    print "\t<root> should be a UT string like 20100101120000, or a parseable filename"
    print "\tCan also give HA,Dec in degrees"
    #print "version=%s" % __version__
    

######################################################################
if __name__ == "__main__":
    main()

        
