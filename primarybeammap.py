#!/usr/bin/env python
"""
primarybeammap.py --freq=202.24 --beamformer=0,0,0,1,3,3,3,3,6,6,6,6,8,9,9,9 --datetimestring=20110926210616

main task is:
make_primarybeammap()

"""
from mwapy import ephem_utils
import primary_beam
import sys
import pyfits,numpy,math
import os,time
from optparse import OptionParser
import ephem
import logging
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as pylab

defaultcolor='k'
defaultsize=8
contourlevels=[0.01, 0.1, 0.25, 0.5, 0.75]
# information for the individual sources to label
# for each, give the name, RA, Dec, color, fontsize, and justification
# if the last three are omitted they will use the defaults
sources={
    'HydA': ['Hyd A','09:18:05.65','-12:05:43.9','b',10,'l'],
    'ForA': ['For A (double)','03:22:41.52','-37:12:33.5',defaultcolor,defaultsize,'l'],
    'PicA': ['Pic A','05:19:49.73','-45:46:43.7','b',10,'l'],
    'EOR1': ['EoR1','04:00:00','-30:00:00','b',12,'c'],
    'EOR2': ['EoR2','10:20:00','-10:00:00','b',12,'c'],
    'PupA': ['Pup A\n(resolved)','08:24:07','-42:59:48'],
    '3C161': ['3C 161','06:27:10.09','-05:53:04.7',defaultcolor,defaultsize,'r'],
    'M42': ['M42/Orion','05:35:17.3','-05:23:28'],
    'CasA': ['Cas A','23:23:24','+58:48:54'],
    'CygA': ['Cyg A','19:59:28.36','+40:44:02.1'],
    '3C444': ['3C 444','22:14:25.75','-17:01:36.3'],
    'PKS0408': ['PKS 0408-65'	 ,'04:08:20.37884'	 ,'-65:45:09.0806'],
    'PKS0410': ['PKS 0410-75'	 ,'04:08:48.4924'	 ,'-75:07:19.327' ],
    'LMC': ['LMC'	         ,'05:23:34.6'	         ,'-69:45:22'     ],
    'PKS2104': ['PKS 2104-25'	 ,'21:07:25.7'	         ,'-25:25:46'     ],
    'PKS2153': ['PKS 2153-69'	 ,'21:57:05.98061'	 ,'-69:41:23.6855'],
    'PKS 1932': ['PKS 1932-46'	 ,'19:35:56.5'     	 ,'-46:20:41' ,'w'    ],
    'PKS1814': ['PKS 1814-63'	 ,'18:19:35.00241'	 ,'-63:45:48.1926'],
    'PKS1610': ['PKS 1610-60'	 ,'16:15:03.864'	 ,'-60:54:26.14' ,'w' ],
    'CenB': ['Cen B'	         ,'13:46:49.0432'	 ,'-60:24:29.355','w' ],
    'CenA': ['Cen A (resolved)'	 ,'13:25:27.61507'	 ,'-43:01:08.8053'],
    '3C310': ['3C 310'	 	 ,'15:04:57.108'	 ,'+26:00:58.28'  ],
    '3C409': ['3C 409'	 	 ,'20:14:27.74'	         ,'+23:34:58.4' ,'w'  ],
    '3C433': ['3C 433'	 	 ,'21:23:44.582'	 ,'+25:04:27.23' ,'w' ],
    'SgrA': ['Sgr A*'	 	 ,'17:45:40.0409'	 ,'-29:00:28.118','w' ],
    'HerA': ['Her A'	 	 ,'16:51:08.147'	 ,'+04:59:33.32',defaultcolor,defaultsize,'r'  ],
    '3C353': ['3C 353'	 	 ,'17:20:28.147'	 ,'-00:58:47.12'  ],
    '3C327': ['3C 327'	 	 ,'16:02:27.39'	         ,'+01:57:55.7'   ],
    '3C317': ['3C 317' 	         ,'15:16:44.487'	 ,'+07:01:18.00',defaultcolor,defaultsize,'r'  ],
    '3C298': ['3C 298'	 	 ,'14:19:08.1788'	 ,'+06:28:34.757',defaultcolor,defaultsize,'r' ],
    'VirA': ['Vir A/M87'	 	 ,'12:30:49.42338'	 ,'+12:23:28.0439','g',defaultsize,'r'],    
    '3C270': ['3C 270'	 	 ,'12:19:23.21621'	 ,'+05:49:29.6948',defaultcolor,defaultsize,'r'],
    '3C273': ['3C 273'	 	 ,'12:29:06.69512'	 ,'+02:03:08.6628',defaultcolor,defaultsize,'r'],
    'PKS2356': ['PKS 2356-61','23:59:04.37','-60:54:59.4'],
    'M1': ['M1/Crab'	 	 ,'05:34:31.93830'	 ,'+22:00:52.1758','g']
    }

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('primarybeammap')
logger.setLevel(logging.WARNING)


radio_image='radio408.RaDec.fits'

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
def sunpositions():
    """
    ra,dec=sunpositions()
    returns the ra,dec in degrees for the Sun for every day of the year
    """
    ra=[]
    dec=[]
    for y in xrange(1,366):
        t=time.strptime("2011 %03d" % y,"%Y %j")
        ras,decs,y,z=sunposition(t.tm_year,
                             t.tm_mon,
                             t.tm_mday,'00:00:00')
        if (ras>180):
            ras-=360
        if (ras<-180):
            ras+=360
 
        ra.append(ras)
        dec.append(decs)
    return ra,dec
            

######################################################################

def main():

    usage="Usage: %prog [options]\n"
    usage+="\tCreates an image of the 408 MHz sky (annoted with sources) that includes contours for the MWA primary beam\n"
    usage+="\tThe beam is monochromatic, and is the sum of the XX and YY beams\n"
    usage+="\tThe date/time (UT) and beamformer delays must be specified\n"
    usage+="\tBeamformer delays should be separated by commas\n"
    usage+="\tFrequency is in MHz, or a coarse channel number (can also be comma-separated list)\n"
    usage+="\tDefault is to plot centered on RA=0, but if -r/--racenter, will center on LST\n"
    usage+="\tContours will be plotted at %s of the peak\n" % contourlevels
    usage+="\tExample:\tpython primarybeammap.py -c 98 --beamformer=1,0,0,0,3,3,3,3,6,6,6,6,9,9,9,8 --datetimestring=20110926211840\n\n"
    
    parser = OptionParser(usage=usage)
    parser.add_option('-d','--datetimestring',dest="datetimestring",default=None,
                      help="Compute for <DATETIMESTRING> (YYYYMMDDhhmmss)",
                      metavar="DATETIMESTRING")
    parser.add_option('-c','--channel',dest='channel',default=None,
                      help='Center channel(s) of observation')
    parser.add_option('-f','--frequency',dest='frequency',default=None,
                      help='Center frequency(s) of observation [MHz]')
    parser.add_option('-b','--beamformer',dest='delays',default=None,
                      help='16 beamformer delays separated by commas')
    parser.add_option('-D','--date',dest='date',default=None,
                      help='UT Date')
    parser.add_option('-t','--time',dest='time',default=None,
                      help='UT Time')
    parser.add_option('-g','--gps',dest='gps',default=None,
                      help='GPS time')
    parser.add_option('--title',dest='title',default=None,
                      help='Plot title')
    parser.add_option('-e','--ext',dest='extension',default='png',
                      help='Plot extension [default=%default]')
    parser.add_option('-r','--racenter',action="store_true",dest="center",default=False,
                      help="Center on LST?")
    parser.add_option('-s','--sunline',dest="sunline",default="1",choices=['0','1'],
                      help="Plot sun [default=%default]")
    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")

    (options, args) = parser.parse_args()
    datetimestring=options.datetimestring
    if options.frequency is not None:
        if (',' in options.frequency):
            try:
                frequency=map(float,options.frequency.split(','))
            except ValueError:
                logger.error("Could not parse frequency %s\n" % options.frequency)
                sys.exit(1)
        else:
            try:
                frequency=float(options.frequency)
            except ValueError:
                logger.error("Could not parse frequency %s\n" % options.frequency)
                sys.exit(1)
    else:
        frequency=options.frequency
    if options.channel is not None:
        if (',' in options.channel):
            try:
                channel=map(float,options.channel.split(','))
            except ValueError:
                logger.error("Could not parse channel %s\n" % options.channel)
                sys.exit(1)
        else:
            try:
                channel=float(options.channel)
            except ValueError:
                logger.error("Could not parse channel %s\n" % options.channel)
                sys.exit(1)
    else:
        channel=options.channel
    if options.delays is not None:
        try:
            if (',' in options.delays):
                delays=map(int,options.delays.split(','))
            else:
                delays=16*[int(options.delays)]
        except:
            logger.error("Could not parse beamformer delays %s\n" % options.delays)
            sys.exit(1)
    else:
        delays=options.delays
    extension=options.extension
    verbose=options.verbose
    title=options.title
    center=options.center
    sunline=int(options.sunline)
    datestring=options.date
    timestring=options.time
    gpsstring=options.gps
               
    if (datetimestring is None):
        if (datestring is not None and timestring is not None):
            datetimestring=datestring.replace('-','') + timestring.replace(':','')
    if gpsstring is not None:
        try:
            mjd,ut=ephem_utils.calcUTGPSseconds(int(gpsstring))
        except:
            logger.error('Cannot convert gpsstring %s to a date/time' % gpsstring)
            sys.exit(1)
        yr,mn,dy=ephem_utils.mjd_cal(mjd)
        datetimestring=('%04d%02d%02d' % (yr,mn,dy))+ ephem_utils.dec2sexstring(ut,digits=0,roundseconds=1).replace(':','')
    if (datetimestring is None):
        logger.error("Must supply a date/time\n")
        sys.exit(1)
    if len(datetimestring) != 14:
        logger.error('Format of date/time is YYYYMMDDhhmmss; %s is not valid\n' % datetimestring)
        sys.exit(1)
        
    if (len(delays)<16):
        logger.error("Must supply 1 or 16 delays\n")
        sys.exit(1)
    if (frequency is None):
        if (channel is not None):
            if (isinstance(channel,list)):
                frequency=list(1.28*numpy.array(channel))
            else:
                frequency=1.28*channel
    if frequency is None:
        logger.error("Must supply frequency or channel\n")
        sys.exit(1)

    result=make_primarybeammap(datetimestring, delays, frequency, center, sunline=sunline,
                               extension=extension, title=title, verbose=verbose)
    if (result is not None):
        print "Wrote %s" % result
                
            

######################################################################
def make_primarybeammap(datetimestring, delays, frequency, center=False, sunline=True,
                        low=1, high=2000, plothourangle=True, extension='png',
                        figsize=8, title=None, verbose=False):
    """
    filename=make_primarybeammap(datetimestring, delays, frequency, center=False, sunline=True,
    low=1, high=2000, plothourangle=True, extension='png', figsize=8, title=None, verbose=False)
    if center==True, will center the image on the LST
    otherwise will have a fixed range (RA=-12 to 12)

    can adjust the grayscale limits

    if plothourangle==True, will also plot x-axis for hour angle
    """
    # protect against log errors
    if (low<=0):
        low=1

    # get the Haslam 408 MHz map
    dir=os.path.dirname(__file__)
    if (len(dir)==0):
        dir='.'
    radio_image_touse=dir + '/' + radio_image

    if not os.path.exists(radio_image_touse):
        logger.error("Could not find 408 MHz image: %s\n" % (radio_image_touse))
        return None
    try:
        if (verbose):
            print "Loading 408 MHz map from %s..." % radio_image_touse
        f=pyfits.open(radio_image_touse)
    except:
        logger.error("Error opening 408 MHz image: %s\n" % (radio_image_touse))
        return None
    skymap=f[0].data[0]
    #x=skymap[:,0].reshape(-1,1)
    #x=skymap[:,0:10]
    #skymap=numpy.concatenate((skymap,x),axis=1)
    ra=(f[0].header.get('CRVAL1')+(numpy.arange(1,skymap.shape[1]+1)-f[0].header.get('CRPIX1'))*f[0].header.get('CDELT1'))/15.0
    dec=f[0].header.get('CRVAL2')+(numpy.arange(1,skymap.shape[0]+1)-f[0].header.get('CRPIX2'))*f[0].header.get('CDELT2')
    
    # parse the datetimestring
    try:
        yr=int(datetimestring[:4])
        mn=int(datetimestring[4:6])
        dy=int(datetimestring[6:8])
        hour=int(datetimestring[8:10])
        minute=int(datetimestring[10:12])
        second=int(datetimestring[12:14])
    except:
        logger.error('Could not parse datetimestring %s\n' % datetimestring)
        return None
    UT=hour+minute/60.0+second/3600.0
    UTs='%02d:%02d:%02d' % (hour,minute,second)
    mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]

    # determine the LST
    observer=ephem.Observer()
    # make sure no refraction is included
    observer.pressure=0
    observer.long=mwa.long/ephem_utils.DEG_IN_RADIAN
    observer.lat=mwa.lat/ephem_utils.DEG_IN_RADIAN
    observer.elevation=mwa.elev
    observer.date='%d/%d/%d %s' % (yr,mn,dy,UTs)
    LST_hours=observer.sidereal_time()*ephem_utils.HRS_IN_RADIAN
    LST=ephem_utils.dec2sexstring(LST_hours,digits=0,roundseconds=1)
    if (verbose):
        print "For %02d-%02d-%02d %s UT, LST=%s" % (yr,mn,dy,UTs,LST)

    # this will be the center of the image
    RA0=0
    if (center):
        RA0=LST_hours*15
    else:
        if (LST_hours>6 and LST_hours<18):
            RA0=180
    
    # use LST to get Az,Alt grid for image
    RA,Dec=numpy.meshgrid(ra*15,dec)
    #HA=RA-LST_hours*15
    HA=-RA+LST_hours*15
    Az,Alt=ephem_utils.eq2horz(HA,Dec,mwa.lat)
    
    # get the horizon line
    Az_Horz=numpy.arange(360.0)
    Alt_Horz=numpy.zeros(Az_Horz.shape)
    HA_Horz,Dec_Horz=ephem_utils.horz2eq(Az_Horz,Alt_Horz,mwa.lat)
    #RA_Horz=HA_Horz+LST_hours*15
    RA_Horz=-HA_Horz+LST_hours*15
    RA_Horz[numpy.where(RA_Horz>180+RA0)[0]]-=360
    RA_Horz[numpy.where(RA_Horz<-180+RA0)[0]]+=360
    
    maskedskymap=numpy.where(Alt>0,skymap,numpy.nan)
    
    # figure out where the Sun will be
    RAsun,Decsun,Azsun,Altsun=sunposition(yr,mn,dy,UT)
    if (RAsun>180+RA0):
        RAsun-=360
    if (RAsun<-180+RA0):
        RAsun+=360
    RAsuns,Decsuns=sunpositions()
    RAsuns=numpy.array(RAsuns)
    Decsuns=numpy.array(Decsuns)
    #HAsuns=RAsuns-LST_hours*15
    HAsuns=-RAsuns+LST_hours*15
    RAsuns=numpy.where(RAsuns>180+RA0,RAsuns-360,RAsuns)
    RAsuns=numpy.where(RAsuns<-180+RA0,RAsuns+360,RAsuns)
    
    # do the plotting
    # this sets up the figure with the right aspect ratio
    fig=pylab.figure(figsize=(figsize,0.5*figsize),dpi=120)
    ax1=fig.add_subplot(1,1,1)
    # this is the Haslam map, plotted as a log-scale
    # it is slightly transparent since this does below the horizon too
    i2=ax1.imshow(numpy.log10(skymap),cmap=pylab.cm.gray_r,aspect='auto',
                  vmin=math.log10(low),vmax=math.log10(high),
                  origin='lower',extent=(ra[0],ra[-1],dec[0],dec[-1]),alpha=0.9)
    i1=ax1.imshow(numpy.log10(maskedskymap),cmap=pylab.cm.gray_r,aspect='auto',
                  vmin=0,vmax=math.log10(2000),
                  origin='lower',extent=(ra[0],ra[-1],dec[0],dec[-1]))
    # this is the Haslam map but only above the horizon
    i2b=ax1.imshow(numpy.log10(skymap),cmap=pylab.cm.gray_r,aspect='auto',
                   vmin=math.log10(low),vmax=math.log10(high),
                   origin='lower',extent=(ra[0]+24,ra[-1]+24,dec[0],dec[-1]),alpha=0.9)
    i1b=ax1.imshow(numpy.log10(maskedskymap),cmap=pylab.cm.gray_r,aspect='auto',
                   vmin=math.log10(low),vmax=math.log10(high),
                   origin='lower',extent=(ra[0]+24,ra[-1]+24,dec[0],dec[-1]))        

    if (isinstance(frequency,float) or isinstance(frequency,int)):
        if (verbose):
            print "Creating primary beam response for frequency %.2f MHz..." % (frequency)
            print "Beamformer delays are %s" % delays
        r=return_beam(Alt,Az,delays,frequency)
        if (r is None):
            return None
        Z2=numpy.where(r>=min(contourlevels),r,0)

        if (verbose):
            i=numpy.nonzero(Z2==Z2.max())
            ramax=RA[i][0]
            if (ramax<0):
                ramax+=360
            print "Sensitivity is max at (RA,Dec)=(%.5f,%.5f)" % (ramax,Dec[i][0])

        # put on contours for the beam
        ax1.contour(RA/15.0,Dec,Z2,contourlevels,colors='r')
        ax1.contour(RA/15.0-24,Dec,Z2,contourlevels,colors='r')
        ax1.contour(RA/15.0+24,Dec,Z2,contourlevels,colors='r')
    else:
        contourcolors=['r','c','y','m','w','g','b']
        icolor=0
        for f in frequency:
            color=contourcolors[icolor]
            if (verbose):
                print "Creating primary beam response for frequency %.2f MHz..." % (f)
                print "Beamformer delays are %s" % delays            
            r=return_beam(Alt,Az,delays,f)
            if r is None:
                return None
            Z2=numpy.where(r>=min(contourlevels),r,0)

            if (verbose):
                i=numpy.nonzero(Z2==Z2.max())
                ramax=RA[i][0]
                if (ramax<0):
                    ramax+=360
                print "Sensitivity is max at (RA,Dec)=(%.5f,%.5f)" % (ramax,Dec[i][0])

            # put on contours for the beam
            ax1.contour(RA/15.0,Dec,Z2,contourlevels,colors=color)
            ax1.contour(RA/15.0-24,Dec,Z2,contourlevels,colors=color)
            ax1.contour(RA/15.0+24,Dec,Z2,contourlevels,colors=color)
            icolor+=1
            if (icolor>=len(contourcolors)):
                icolor=0

    # plot the horizon line
    RA_Horz,Dec_Horz=zip(*sorted(zip(RA_Horz,Dec_Horz)))
    p1=ax1.plot(numpy.array(RA_Horz)/15.0,numpy.array(Dec_Horz),'k')
    x1=12+RA0/15
    x2=-12+RA0/15
    ax1.set_xlim(left=x1,right=x2)
    ax1.set_ylim(bottom=-90,top=90)
    ax1.set_xticks(numpy.arange(-12+int(RA0/15),15+int(RA0/15),3))
    l=[]
    for x in numpy.arange(-12+int(RA0/15),15+int(RA0/15),3):
        if (x>=0 and x<24):
            l.append('%d' % x)
        elif (x>=24):
            l.append('%d' % (x-24))
        else:
            l.append('%d' % (x+24))
    ax1.set_xticklabels(l)
    ax1.set_yticks(numpy.arange(-90,105,15))
    ax1.set_xlabel('Right Ascension (hours)')
    ax1.set_ylabel('Declination (degrees)')
    # plot the Sun
    ax1.plot(RAsun/15.0,Decsun,'yo',markersize=10)
    RAsuns,Decsuns=zip(*sorted(zip(RAsuns,Decsuns)))
    if (sunline):
        ax1.plot(numpy.array(RAsuns)/15.0,numpy.array(Decsuns),'y-')
    # add text for sources
    for source in sources:
        r=ephem_utils.sexstring2dec(sources[source][1])
        d=ephem_utils.sexstring2dec(sources[source][2])
        horizontalalignment='left'
        x=r-0.2
        if (len(sources[source])>=6 and sources[source][5]=='c'):    
            horizontalalignment='center'
            x=r
        if (len(sources[source])>=6 and sources[source][5]=='r'):    
            horizontalalignment='right'
            x=r+0.1        
        if (x>12+RA0/15):
            x-=24
        if (x<-12+RA0/15):
            x+=24
        fontsize=defaultsize
        if (len(sources[source])>=5):
            fontsize=sources[source][4]
        color=defaultcolor
        if (len(sources[source])>=4):
            color=sources[source][3]
        ax1.text(x,d,sources[source][0],horizontalalignment=horizontalalignment,
                 fontsize=fontsize,color=color,
                 verticalalignment='center')

    if (isinstance(frequency,int) or isinstance(frequency,float)):

        textlabel='%04d-%02d-%02d %02d:%02d:%02d %.2f MHz' % (yr,mn,dy,hour,
                                                              minute,
                                                              second,
                                                              frequency)
    else:
        
        fstring="[" + ','.join(["%.2f" % f for f in frequency]) + "]"
        textlabel='%04d-%02d-%02d %02d:%02d:%02d %s MHz' % (yr,mn,dy,hour,
                                                              minute,
                                                              second,
                                                            fstring)
        icolor=0
        for i in xrange(len(frequency)):
            color=contourcolors[icolor]
            ax1.text(x1-1,70-10*i,'%.2f MHz' % frequency[i],
                     fontsize=12,color=color,horizontalalignment='left')
            icolor+=1
            if (icolor>=len(contourcolors)):
                icolor=0

    if title is not None:
        title=title.replace('_','\_')
        textlabel=title + ' ' + textlabel
    if (plothourangle):
        ax2=ax1.twiny()
        p=ax2.plot(HAsuns/15,Decsuns,'y-')
        p[0].set_visible(False)
        ax1.set_ylim(bottom=-90,top=90)
        ax2.set_ylim(bottom=-90,top=90)
        ax1.set_yticks(numpy.arange(-90,105,15))
        #x1b=x1-LST_hours
        #x2b=x2-LST_hours
        x1b=-x1+LST_hours
        x2b=-x2+LST_hours
        while (x1b<0):
            x1b+=24
        while (x1b>24):
            x1b-=24
        x2b=x1b-24
        ax2.set_xlim(left=x2b,right=x1b)
        ax2.set_xlabel('Hour Angle (hours)')
        ax1.text(x1-1,80,textlabel,
                 fontsize=14,horizontalalignment='left')
    else:
        ax1.set_title(textlabel)


    #print ax1.get_xlim()
    #try:
    #    print ax2.get_xlim()
    #except:
    #    pass
    if (isinstance(frequency,int) or isinstance(frequency,float)):
        filename='%s_%.2fMHz.%s' % (datetimestring,frequency,extension)
    else:
        filename='%s_%.2fMHz.%s' % (datetimestring,frequency[0],extension)
    try:
        pylab.savefig(filename)
    except RuntimeError,err:
        logger.error('Error saving figure: %s\n' % err)
        return None

    return filename

######################################################################
def return_beam(Alt,Az,delays,frequency):
    """
    r=return_beam(Alt,Az,delays,frequency)
    frequency in MHz
    returns the normalized combined XX/YY response
    """
    # get the beam response
    # first go from altitude to zenith angle
    theta=(90-Alt)*math.pi/180
    phi=Az*math.pi/180

    # this is the response for XX and YY
    try:
        respX,respY=primary_beam.MWA_Tile_analytic(theta,phi,freq=frequency*1e6,delays=numpy.array(delays))
    except:
        logger.error('Error creating primary beams\n')
        return None
    rX=numpy.real(numpy.conj(respX)*respX)
    rY=numpy.real(numpy.conj(respY)*respY)
    # make a pseudo-I beam
    r=rX+rY
    # normalize
    r/=numpy.nanmax(r)
    return r


######################################################################
# Running as executable
if __name__=='__main__':
    main()
