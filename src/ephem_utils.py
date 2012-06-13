#!/usr/bin/env python

"""
ephem_utils.py

python classes/routines to implement various ephemeris/source position related routines

-) Make sure hourangle definition is correct
   should be HA=LST-RA
   or RA=LST-HA


$Rev$:     Revision of last commit
$Author$:  Author of last commit
$Date$:    Date of last commit


"""


import os, sys, string, re, types, math, copy, logging
import getopt,datetime
import time
import numpy.numarray as numarray
import numpy
import ephem
#####################################################################
# Constants    

dow={0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'}
# J2000.0 in MJD
J2000=51544.5
DEG_IN_RADIAN=180/math.pi
HRS_IN_RADIAN=180/math.pi/15
# equatorial radius of earth, meters
EQUAT_RAD=6378137.0
SEC_IN_DAY=86400
# flattening of earth, 1/298.257
FLATTEN=0.003352813
# GPS seconds defined as seconds since Jan 06, 1980
# this is MJD 44244
# what about leap seconds?
GPSseconds_MJDzero=44244.0

# from time.sql
# written by EHM
# data for GPSseconds to UTC conversion
# containing the UTC dates that various leapseconds occured
# updated by CW
MJD_Start=[49169, 49534, 50083, 50630, 51179, 53736,54832]
MJD_End=[49534, 50083, 50630, 51179, 53736, 54832, 99999]
GPSseconds_Start=[425520008, 457056009, 504489610, 551750411, 599184012, 820108813,914803214]
GPSseconds_End=[457056009, 504489610, 551750411, 599184012,820108813, 914803214, 9223372036854775807]
Offset_seconds=[315964791, 315964790, 315964789, 315964788, 315964787, 315964786, 315964785]


######################################################################
# OBJECT DEFINITIONS
######################################################################



######################################################################
class Observatory(object):

    def __init__(self,code='NULL',name='None',long=0,lat=0,elev=0,stdtz=0,use_dst=0,stcode="X"):
        self.lat=checksex(lat)
        self.long=checksex(long)
        self.name=name
        self.code=code
        self.elev=elev
        self.stdtz=stdtz
        self.use_dst=use_dst
        self.year=0
        self.tz=stdtz
        self.stcode=stcode
        # now compute derived quantity "horiz" = depression of horizon
        self.horiz=math.sqrt(2*self.elev/EQUAT_RAD)*DEG_IN_RADIAN

    ##################################################
    def __str__(self):
        s="Observatory %s: %s at (%s,%s)\n" % (self.code,self.name,dec2sexstring(self.long,digits=-1),dec2sexstring(self.lat,1,digits=-1))
        if (self.tz > 0):
            tzsign='-'
            tzval=self.tz
        else:
            tzsign='+'
            tzval=-self.tz
        s2="\tElev=%d m, Time=UT%s%d h, DST_Conv=%s (DST=%d)" % (self.elev,tzsign,tzval,self.dst_string(),not self.tz==self.stdtz)
        return "%s %s" % (s,s2)

    ##################################################
    def dst_string(self):
        if (self.use_dst==1):
            return 'US'
        if (self.use_dst==-1):
            return 'Chile'
        if (self.use_dst==0):
            return 'None'
        if (self.use_dst==-2):
            return 'Australia'
            
######################################################################
class Object(object):
    """ ra in hours, dec in degrees """


    def __init__(self,name='None',ra=None,dec=None,epoch='J2000'):
        # ra in hours, dec in degrees        
        self.ra=(checksex(ra))
        self.dec=checksex(dec)
        self.name=name
        self.epoch=epoch

    ##################################################
    def __str__(self):
        return "Object %s: (%s,%s) (%s)" % (self.name,dec2sexstring(self.ra),dec2sexstring(self.dec,includesign=1),self.epoch)

    ##################################################
    def copy(self):
        return Object(self.name,self.ra,self.dec,self.epoch)

    ##################################################
    def galactic(self):
        """
        galactic(self)
        convert to galactic coords
        """
        [l,b]=adtolb(self.ra/HRS_IN_RADIAN,self.dec/DEG_IN_RADIAN)
        return [l*DEG_IN_RADIAN,b*DEG_IN_RADIAN]

    ##################################################
    def getl(self):
        [l,b]=self.galactic()
        return l

    ##################################################
    def getb(self):
        [l,b]=self.galactic()
        return b

    l=property(getl,doc='Galactic Longitude')
    b=property(getb,doc='Galactic Latitude')

    
    ##################################################
    def angulardistance(self,obj2):
        """
        angle=object1.angulardistance(object2)
        angle subtended by two positions in the sky
        result is in radians
        
        based on angulardistance()
        """
        [ra1,dec1]=[self.ra,self.dec]
        [ra2,dec2]=[obj2.ra,obj2.dec]

        return angulardistance(ra1,dec1,ra2,dec2)


######################################################################
class Time(Observatory):

    def __init__(self,obs=None):
        self.isinit=0
        self.obs=obs
        self.MJD=0
        self.LST=0
        self.utmlt=0
        self.isdst=0
        self.UT=0
        self.LT=0
        self.__dict__['GPSseconds']=0
        self.epoch=mjd_to_epoch(self.MJD)
        if (self.obs==None):
            self.LTtype="XST"
        else:
            self.LTtype="%sST" % (self.obs.stcode)

    ##################################################
    def __str__(self):
        s=str(self.obs)
        [yr,mn,dy]=mjd_cal(self.MJD)
        s+="\nMJD %.1f %d-%02d-%02d UT=%s %s=%s LMST=%s GPSseconds=%.1f" % (self.MJD+self.UT/24.0,yr,mn,dy,dec2sexstring(self.UT),self.LTtype,dec2sexstring(self.LT),dec2sexstring(self.LST),self.GPSseconds)
        if (not self.isinit):
            s+="\nTime not initialized!"
        return s

    ##################################################
    def __repr__(self):
        return str(self)

    ##################################################
    def calctz(self):
        [yr,mn,dy]=mjd_cal(self.MJD)
        [mjdb,mjde]=find_dst_bounds(yr,self.obs.stdtz,self.obs.use_dst)
        self.utmlt=zonetime(self.obs.use_dst,self.obs.stdtz,self.MJD,mjdb,mjde)
        if (self.utmlt != self.obs.stdtz):
            self.isdst=1
            self.LTtype="%sDT" % (self.obs.stcode)
        self.obs.year=yr
        self.obs.tz=self.utmlt
        self.isinit=1

    ##################################################
    def __getattr__(self,name):
        if (not self.__dict__.has_key(name)):
            try:
                return self.obs.__dict__[name]
            except (AttributeError,TypeError):
                logging.warning("Attribute %s not defined for class Time" % name)
                return None
        else:
            return self.__dict__[name]

        
    ##################################################
    def __setattr__(self,name,value):
        if (name == "UT"):
            # if we assign a value to UT
            # update LT, MJD (if necessary), epoch, and LST
            self.__dict__[name]=putrange(value)
            #while (value<0):
            #    self.MJD-=1
            #    value+=24
            #while (value>=24):
            #    self.MJD+=1
            #    value-=24
            self.epoch=mjd_to_epoch(self.MJD+value/24.0)
            if (self.obs != None):
                self.__dict__["LT"]=putrange(value-self.utmlt)
                self.LST=utc_lmst(self.MJD+value/24.0,self.obs.long)
            if (self.isinit):
                self.setGPSseconds()
        elif (name == "LT"):
            # if we assign a value to LT
            # update UT and thereby LST
            self.__dict__[name]=putrange(value)
            self.UT=value+self.utmlt
            if (self.isinit):
                self.setGPSseconds()
        elif (name == "GPSseconds"):
            # if we assign a time in GPS seconds
            self.__dict__[name]=value
            self.setutGPS()
        else:
            self.__dict__[name]=value



    ##################################################
    def init(self,MJD,time,islt=1):
        """ initialize a time instance
        this involves setting the date (MJD) and time (local or UT)
        then determining the appropriate time zone
        then resetting the date & time
        then calculating LST
        """
        self.MJD=MJD
        if (islt):
            self.LT=time
        else:
            self.UT=time        
        self.calctz()
        self.MJD=MJD
        if (islt):
            self.LT=time
        else:
            self.UT=time        
        self.setGPSseconds()

    ##################################################
    def init_datetime(self,d):
        """
        initializes the Time data from the information
        in the datetime.datetime object d
        """
        if (not d.tzinfo):
            # the timezone info is null: assume UT
            # (I think this is not always true: often the TZ info is just
            # not properly set, even if it's not UT)
            self.init(cal_mjd(d.year,d.month,d.day),d.hour+d.minute/60.0+d.second/3600.0+d.microsecond/3600.0/1e6,islt=0)
        else:
            # don't know how to handle it
            logging.warning("Unknown timezone information for datetime %s: %s...\n" % (d,d.tzinfo))
                          
    ##################################################
    def datetime(self):
        """
        returns the date/time information in self as a datetime.datetime object
        gives data in UT
        """
        [yr,mn,dy]=mjd_cal(self.MJD)
        [hr,min,sec]=dec2sex(self.UT)
        usec=int(sec*1e6)        
        d=datetime.datetime(yr,mn,dy,hr,min,int(sec),usec,None)
        return d
    

    ##################################################
    def setGPSseconds(self):
        """
        set GPSseconds based on a MJD and UT time
        """
        self.__dict__["GPSseconds"]=calcGPSseconds(self.MJD,self.UT)

    ##################################################
    def setutGPS(self):
        """
        set UT time based on GPS seconds
        """
        [MJD,UT]=calcUTGPSseconds(self.GPSseconds)
        self.setut(MJD,UT)
        
    ##################################################
    def setut(self,mjd,ut):
        self.MJD=mjd
        self.UT=ut
        if (self.UT<0):
            self.MJD-=1
            self.UT+=24
        if (self.UT>=24):
            self.MJD+=1
            self.UT-=24
        self.LT=self.UT-self.utmlt
        self.LT=putrange(self.LT)
        self.LST=utc_lmst(self.MJD+self.UT/24.0,self.obs.long)
        self.epoch=mjd_to_epoch(self.MJD)
        self.setGPSseconds()

    ##################################################        
    def setlt(self,mjd,lt):
        self.MJD=mjd
        self.LT=lt
        self.UT=self.LT+self.utmlt
        if (self.UT<0):
            self.MJD-=1
            self.UT+=24
        if (self.UT>=24):
            self.MJD+=1
            self.UT-=24
        if (self.LT<0):
            self.LT+=24
        if (self.LT>=24):
            self.LT-=24            

        self.LST=utc_lmst(self.MJD+self.UT/24.0,self.obs.long)
        self.epoch=mjd_to_epoch(self.MJD)
        self.setGPSseconds()


    ##################################################
    def zenith(self):
        """
        zenith=zenith()
        returns an Object containing the  RA(hrs) and Dec(deg) of the zenith
        """
        s="Zenith for %s at MJD %.1f (UT)" % (self.obs.name,self.MJD+self.UT/24.0)
        return Object(s,self.LST,self.lat)

    ##################################################
    def copy(self):
        t=Time(self.obs)
        t.init(self.MJD,self.UT,islt=0)
        return t


######################################################################
class Moon(Object,Time):

    def __init__(self,tm):
        self.obj=Object("Moon",0,0,mjd_to_epoch(tm.MJD))
        self.tm=tm
        self.calc()

    ##################################################
    def calc(self,accu=1):
        if (not accu):
            # use low precision
            [ra_moon,dec_moon,dist_moon]=lpmoon(self.tm.MJD+self.tm.UT/24.0,self.tm.obs.lat/15,self.tm.LST)
        else:
            [ra_moon,dec_moon,dist_moon,ra_moon2,dec_moon2,dist_moon2]=accumoon(self.tm.MJD+self.tm.UT/24.0,self.tm.obs.lat,self.tm.LST,self.tm.obs.elev)
            # get topocentric
            [ra_moon,dec_moon,dist_moon]=[ra_moon2,dec_moon2,dist_moon2]

        [ra_sun,dec_sun]=lpsun(self.tm.MJD+self.tm.UT/24.0)
        temp_sun=Object("temp_sun",ra_sun,dec_sun)
        self.obj.ra=ra_moon
        self.obj.dec=dec_moon
        ill_frac=0.5*(1-math.cos(self.angulardistance(temp_sun)))
        self.ill_frac=ill_frac

        
        [min_alt,max_alt]=min_max_alt(self.tm.obs.lat,self.obj.dec)
        if (max_alt < -(0.83+self.tm.obs.horiz)):
            print "Moon's midnight position does not rise\n"
        if (min_alt > -(0.83+self.tm.obs.horiz)):
            print "Moon's mignight position does not set\n"

        # compute moonrise and set if they're likely to occur
        hamoonset=ha_alt(self.obj.dec,self.tm.obs.lat,-(0.83+self.tm.obs.horiz))
        tmoonrise=adj_time(self.obj.ra-hamoonset-self.tm.LST)
        tmoonset=adj_time(self.obj.ra+hamoonset-self.tm.LST)
        mjdmoonrise=(self.tm.MJD+self.tm.UT/24.0+tmoonrise/24.0)
        mjdmoonrise=mjd_moon_alt(-(0.83+self.tm.obs.horiz),mjdmoonrise,self.tm.obs.lat,self.tm.obs.long,self.tm.obs.elev)
        mjdmoonset=self.tm.MJD+self.tm.UT/24.0+tmoonset/24.0
        mjdmoonset=mjd_moon_alt(-(0.83+self.tm.obs.horiz),mjdmoonset,self.tm.obs.lat,self.tm.obs.long,self.tm.obs.elev)
        self.mjdrise=mjdmoonrise
        self.mjdset=mjdmoonset
        
    ##################################################
    def __str__(self):
        s="Moon (%s,%s): " % (dec2sexstring(self.obj.ra,digits=0),dec2sexstring(self.obj.dec,1,digits=0))
        if (self.mjdrise < self.mjdset):
            s+="rise %s %s, set %s %s (%5.0fm horiz)\n" % (dec2sexstring(24*frac(self.mjdrise-self.tm.utmlt/24.0),digits=0),self.tm.LTtype,dec2sexstring(24*frac(self.mjdset-self.tm.utmlt/24.0),digits=0),self.tm.LTtype,self.tm.obs.elev)
        else:
            s+="set %s %s, rise %s %s (%5.0fm horiz)\n" % (dec2sexstring(24*frac(self.mjdset-self.tm.utmlt/24.0),digits=0),self.tm.LTtype,dec2sexstring(24*frac(self.mjdrise-self.tm.utmlt/24.0),digits=0),self.tm.LTtype,self.tm.obs.elev)                    
        s+="\t%d percent illum" % (100*self.ill_frac)

        return s

    ##################################################
    def __getattr__(self,name):
        try:
            return self.__dict__[name]
        except KeyError:
            return self.obj.__dict__[name]


######################################################################
class Sun(Object,Time):

    ##################################################
    def __init__(self,tm):
        self.obj=Object("Sun",0,0,mjd_to_epoch(tm.MJD))
        self.tm=tm
        self.calc()

    ##################################################
    def calc(self):
        [ra_sun,dec_sun]=lpsun(self.tm.MJD+self.tm.UT/24.0)
        self.obj.ra=ra_sun
        self.obj.dec=dec_sun
        hasunset=ha_alt(self.obj.dec,self.tm.obs.lat,-(0.83+self.tm.obs.horiz))
        if (hasunset > 900):
            print "Sun up all night!\n"
        if (hasunset < -900):
            print "Sun never up!\n"
        # initial guess for sunset
        mjdsunset=self.tm.MJD+self.tm.UT/24.0+adj_time(self.obj.ra+hasunset-self.tm.LST)/24.0
        mjdsunrise=self.tm.MJD+self.tm.UT/24.0+adj_time(self.obj.ra-hasunset-self.tm.LST)/24.0
        mjdsunset=mjd_sun_alt(-(0.83+self.tm.obs.horiz),mjdsunset,self.tm.obs.lat,self.tm.obs.long)
        mjdsunrise=mjd_sun_alt(-(0.83+self.tm.obs.horiz),mjdsunrise,self.tm.obs.lat,self.tm.obs.long)
        self.mjdrise=mjdsunrise
        self.mjdset=mjdsunset
        # twilight (18 degr)
        hatwilight = ha_alt(self.obj.dec,self.tm.obs.lat,-18.)
        # compute  evening twilight and LST at eve. twilight
        mjdtwilight=self.tm.MJD+self.tm.UT/24.0+adj_time(self.obj.ra+hatwilight-self.tm.LST)/24.0
        mjdtwilight=mjd_sun_alt(-18,mjdtwilight,self.tm.obs.lat,self.tm.obs.long)
        self.mjdevetwilight=mjdtwilight
        self.lstevetwilight=utc_lmst(self.mjdevetwilight,self.tm.obs.long)
        # compute morning twilight and LST at eve. twilight
        mjdtwilight=self.tm.MJD+self.tm.UT/24.0+adj_time(self.obj.ra-hatwilight-self.tm.LST)/24.0
        mjdtwilight=mjd_sun_alt(-18,mjdtwilight,self.tm.obs.lat,self.tm.obs.long)
        self.mjdmortwilight=mjdtwilight
        self.lstmortwilight=utc_lmst(self.mjdmortwilight,self.tm.obs.long)

    ##################################################
    def __str__(self):
        x1=24*frac(self.mjdset-self.tm.utmlt/24.0)
        x2=24*frac(self.mjdrise-self.tm.utmlt/24.0)
        s="Sun (%s,%s): set %s %s, rise %s %s (%5.0fm horiz)\n" % (dec2sexstring(self.obj.ra,digits=0),dec2sexstring(self.obj.dec,1,digits=0),dec2sexstring(x1,digits=0),self.tm.LTtype,dec2sexstring(x2,digits=0),self.tm.LTtype,self.tm.obs.elev)
        x3=24*frac(self.mjdevetwilight-self.tm.utmlt/24.0)
        s+="\t18 degree evening twilight: %s %s = %s LST\n" % (dec2sexstring(x3,digits=0),self.tm.LTtype,dec2sexstring(self.lstevetwilight,digits=0))
        x4=24*frac(self.mjdmortwilight-self.tm.utmlt/24.0)
        s+="\t18 degree morning twilight: %s %s = %s LST" % (dec2sexstring(x4,digits=0),self.tm.LTtype,dec2sexstring(self.lstmortwilight,digits=0))
        return s

    ##################################################
    def __getattr__(self,name):
        try:
            return self.__dict__[name]
        except KeyError:
            return self.obj.__dict__[name]


    ##################################################
    def angulardistance(self,obj2):
        """
        angle=object1.angulardistance(object2)
        angle subtended by two positions in the sky
        result is in radians
        
        based on angulardistance()
        """
        return self.obj.angulardistance(obj2)

######################################################################
# using the pyephem package    
######################################################################
class eSun(Object,Time,ephem.Sun):

    ##################################################
    def __init__(self,tm):
        self.obj=Object("Sun",0,0,mjd_to_epoch(tm.MJD))
        self.Sun=ephem.Sun()
        self.obs=ephem.Observer()
        # make sure no refraction is included
        self.obs.pressure=0
        self.tm=tm
        self.calc()

    ##################################################
    def calc(self):
        self.obs.long=self.tm.long/DEG_IN_RADIAN
        self.obs.lat=self.tm.lat/DEG_IN_RADIAN
        self.obs.elevation=self.tm.elev
        #self.obs.horizon=self.tm.horiz
        [yr,mn,dy]=mjd_cal(self.tm.MJD)
        self.obs.date='%d/%d/%f' % (yr,mn,dy+self.tm.UT/24.0)
        self.Sun.compute(self.obs)
        # these should be topocentric apparent
        self.obj.ra=self.Sun.ra*HRS_IN_RADIAN
        self.obj.dec=self.Sun.dec*DEG_IN_RADIAN
        if (self.Sun.alt > 0):
            # Sun is currently up
            # look for last rising, next setting
            date_rise=self.obs.previous_rising(self.Sun)
            (yr,mn,dy,hr,m,s)=date_rise.tuple()
            self.mjdrise=cal_mjd(yr,mn,dy)+(hr+m/60.0+s/3600.0)/24.0
            date_set=self.obs.next_setting(self.Sun)
            (yr,mn,dy,hr,m,s)=date_set.tuple()        
            self.mjdset=cal_mjd(yr,mn,dy)+(hr+m/60.0+s/3600.0)/24.0
            # 18 degree twilight
            self.obs.horizon='-18:00'
            [yr,mn,dy]=mjd_cal(self.tm.MJD)
            self.obs.date='%d/%d/%f' % (yr,mn,dy+self.tm.UT/24.0)
            self.Sun.compute(self.obs)
            date_mortwi=self.obs.previous_rising(self.Sun)
            (yr,mn,dy,hr,m,s)=date_mortwi.tuple()        
            self.mjdmortwilight=cal_mjd(yr,mn,dy)+(hr+m/60.0+s/3600.0)/24.0 
            date_evetwi=self.obs.next_setting(self.Sun)
            (yr,mn,dy,hr,m,s)=date_evetwi.tuple()        
            self.mjdevetwilight=cal_mjd(yr,mn,dy)+(hr+m/60.0+s/3600.0)/24.0 
            self.lstevetwilight=utc_lmst(self.mjdevetwilight,self.tm.obs.long)
            self.lstmortwilight=utc_lmst(self.mjdmortwilight,self.tm.obs.long)

        else:
            # sun is currently down
            # it's night, so look for next rising, last setting
            date_rise=self.obs.next_rising(self.Sun)
            (yr,mn,dy,hr,m,s)=date_rise.tuple()
            self.mjdrise=cal_mjd(yr,mn,dy)+(hr+m/60.0+s/3600.0)/24.0
            date_set=self.obs.previous_setting(self.Sun)
            (yr,mn,dy,hr,m,s)=date_set.tuple()        
            self.mjdset=cal_mjd(yr,mn,dy)+(hr+m/60.0+s/3600.0)/24.0
            # 18 degree twilight
            self.obs.horizon='-18:00'
            [yr,mn,dy]=mjd_cal(self.tm.MJD)
            self.obs.date='%d/%d/%f' % (yr,mn,dy+self.tm.UT/24.0)
            self.Sun.compute(self.obs)
            date_mortwi=self.obs.next_rising(self.Sun)
            (yr,mn,dy,hr,m,s)=date_mortwi.tuple()        
            self.mjdmortwilight=cal_mjd(yr,mn,dy)+(hr+m/60.0+s/3600.0)/24.0 
            date_evetwi=self.obs.previous_setting(self.Sun)
            (yr,mn,dy,hr,m,s)=date_evetwi.tuple()        
            self.mjdevetwilight=cal_mjd(yr,mn,dy)+(hr+m/60.0+s/3600.0)/24.0 
            self.lstevetwilight=utc_lmst(self.mjdevetwilight,self.tm.obs.long)
            self.lstmortwilight=utc_lmst(self.mjdmortwilight,self.tm.obs.long)


    ##################################################
    def __str__(self):
        x1=24*frac(self.mjdset-self.tm.utmlt/24.0)
        x2=24*frac(self.mjdrise-self.tm.utmlt/24.0)
        s="Sun (%s,%s): set %s %s, rise %s %s (%5.0fm horiz)\n" % (dec2sexstring(self.obj.ra,digits=0),dec2sexstring(self.obj.dec,1,digits=0),dec2sexstring(x1,digits=0),self.tm.LTtype,dec2sexstring(x2,digits=0),self.tm.LTtype,self.tm.obs.elev)
        x3=24*frac(self.mjdevetwilight-self.tm.utmlt/24.0)
        s+="\t18 degree evening twilight: %s %s = %s LST\n" % (dec2sexstring(x3,digits=0),self.tm.LTtype,dec2sexstring(self.lstevetwilight,digits=0))
        x4=24*frac(self.mjdmortwilight-self.tm.utmlt/24.0)
        s+="\t18 degree morning twilight: %s %s = %s LST" % (dec2sexstring(x4,digits=0),self.tm.LTtype,dec2sexstring(self.lstmortwilight,digits=0))
        return s

    ##################################################
    def __getattr__(self,name):
        try:
            return self.__dict__[name]
        except KeyError:
            return self.obj.__dict__[name]

######################################################################
class eMoon(Object,Time,ephem.Moon):

    def __init__(self,tm):
        self.obj=Object("Moon",0,0,mjd_to_epoch(tm.MJD))
        self.tm=tm
        self.Moon=ephem.Moon()
        self.obs=ephem.Observer()
        # make sure no refraction is included
        self.obs.pressure=0
        self.calc()

    ##################################################
    def calc(self):
        self.obs.long=self.tm.long/DEG_IN_RADIAN
        self.obs.lat=self.tm.lat/DEG_IN_RADIAN
        self.obs.elevation=self.tm.elev
        #self.obs.horizon=self.tm.horiz
        [yr,mn,dy]=mjd_cal(self.tm.MJD)
        self.obs.date='%d/%d/%f' % (yr,mn,dy+self.tm.UT/24.0)
        self.Moon.compute(self.obs)

        # these should be topocentric apparent
        self.obj.ra=self.Moon.ra*HRS_IN_RADIAN
        self.obj.dec=self.Moon.dec*DEG_IN_RADIAN

        temp_sun=eSun(self.tm)
        ill_frac=0.5*(1-math.cos(self.obj.angulardistance(temp_sun.obj)))
        self.ill_frac=ill_frac

        
        [min_alt,max_alt]=min_max_alt(self.tm.obs.lat,self.obj.dec)
        if (max_alt < -(0.83+self.tm.obs.horiz)):
            print "Moon's midnight position does not rise\n"
        if (min_alt > -(0.83+self.tm.obs.horiz)):
            print "Moon's mignight position does not set\n"

        if (self.Moon.alt > 0):
            # Moon is currently up
            # look for last rising, next setting
            date_rise=self.obs.previous_rising(self.Moon)
            (yr,mn,dy,hr,m,s)=date_rise.tuple()
            self.mjdrise=cal_mjd(yr,mn,dy)+(hr+m/60.0+s/3600.0)/24.0
            date_set=self.obs.next_setting(self.Moon)
            (yr,mn,dy,hr,m,s)=date_set.tuple()        
            self.mjdset=cal_mjd(yr,mn,dy)+(hr+m/60.0+s/3600.0)/24.0
        else:
            # look for next rising, last setting
            date_rise=self.obs.next_rising(self.Moon)
            (yr,mn,dy,hr,m,s)=date_rise.tuple()
            self.mjdrise=cal_mjd(yr,mn,dy)+(hr+m/60.0+s/3600.0)/24.0
            date_set=self.obs.previous_setting(self.Moon)
            (yr,mn,dy,hr,m,s)=date_set.tuple()        
            self.mjdset=cal_mjd(yr,mn,dy)+(hr+m/60.0+s/3600.0)/24.0

        
    ##################################################
    def __str__(self):
        s="Moon (%s,%s): " % (dec2sexstring(self.obj.ra,digits=0),dec2sexstring(self.obj.dec,1,digits=0))
        if (self.mjdrise < self.mjdset):
            s+="rise %s %s, set %s %s (%5.0fm horiz)\n" % (dec2sexstring(24*frac(self.mjdrise-self.tm.utmlt/24.0),digits=0),self.tm.LTtype,dec2sexstring(24*frac(self.mjdset-self.tm.utmlt/24.0),digits=0),self.tm.LTtype,self.tm.obs.elev)
        else:
            s+="set %s %s, rise %s %s (%5.0fm horiz)\n" % (dec2sexstring(24*frac(self.mjdset-self.tm.utmlt/24.0),digits=0),self.tm.LTtype,dec2sexstring(24*frac(self.mjdrise-self.tm.utmlt/24.0),digits=0),self.tm.LTtype,self.tm.obs.elev)                    
        s+="\t%d percent illum" % (100*self.ill_frac)

        return s
    ##################################################
    def __getattr__(self,name):
        try:
            return self.__dict__[name]
        except KeyError:
            return self.obj.__dict__[name]

######################################################################
# Moon routines
######################################################################

######################################################################
def lpmoon(mjd,lat,lst):
    """
    implements 'low precision' moon algorithms from
    Astronomical Almanac (p. D46 in 1992 version).  Does
    apply the topocentric correction.
    Units are as follows
    jd
    lat, sid;   decimal hours
    ra, dec,   decimal hours, degrees
    dist;      earth radii

    from skycalcv5
    """

    # centuries since J2000.0
    T=(mjd-J2000)/36525
    lmbda = 218.32 + 481267.883 * T
    lmbda += 6.29 * math.sin((134.9 + 477198.85 * T) / DEG_IN_RADIAN)
    lmbda -= 1.27 * math.sin((259.2 - 413335.38 * T) / DEG_IN_RADIAN)
    lmbda += 0.66 * math.sin((235.7 + 890534.23 * T) / DEG_IN_RADIAN)
    lmbda += 0.21 * math.sin((269.9 + 954397.70 * T) / DEG_IN_RADIAN)
    lmbda -= 0.19 * math.sin((357.5 + 35999.05 * T) / DEG_IN_RADIAN)
    lmbda -= 0.11 * math.sin((186.6 + 966404.05 * T) / DEG_IN_RADIAN)
    lmbda/=DEG_IN_RADIAN

    beta = 5.13 * math.sin((93.3 + 483202.03 * T) / DEG_IN_RADIAN)
    beta += 0.28 * math.sin((228.2 + 960400.87 * T) / DEG_IN_RADIAN)
    beta -= 0.28 * math.sin((318.3 + 6003.18 * T) / DEG_IN_RADIAN)
    beta -= 0.17 * math.sin((217.6 - 407332.20 * T) / DEG_IN_RADIAN)
    beta = beta / DEG_IN_RADIAN

    pie = 0.9508
    pie+= 0.0518 * math.cos((134.9 + 477198.85 * T) / DEG_IN_RADIAN)
    pie+= 0.0095 * math.cos((259.2 - 413335.38 * T) / DEG_IN_RADIAN)
    pie+= 0.0078 * math.cos((235.7 + 890534.23 * T) / DEG_IN_RADIAN)
    pie+= 0.0028 * math.cos((269.9 + 954397.70 * T) / DEG_IN_RADIAN)
    pie = pie / DEG_IN_RADIAN
    distance = 1 / math.sin(pie)

    l = math.cos(beta) * math.cos(lmbda)
    m = 0.9175 * math.cos(beta) * math.sin(lmbda) - 0.3978 * math.sin(beta)
    n = 0.3978 * math.cos(beta) * math.sin(lmbda) + 0.9175 * math.sin(beta)
    
    x = l * distance
    y = m * distance
    z = n * distance  
    # for topocentric correction 

    rad_lat = lat / DEG_IN_RADIAN
    rad_lst = lst / HRS_IN_RADIAN
    x = x - math.cos(rad_lat) * math.cos(rad_lst)
    y = y - math.cos(rad_lat) * math.sin(rad_lst)
    z = z - math.sin(rad_lat)

    topo_dist = math.sqrt(x * x + y * y + z * z)

    l = x / topo_dist
    m = y / topo_dist
    n = z / topo_dist

    alpha=math.atan2(m,l)
    alpha=putrange(alpha,math.pi*2)
    delta=math.asin(n)
    ra=alpha*DEG_IN_RADIAN/15
    dec=delta*DEG_IN_RADIAN
    dist=topo_dist
    return (ra,dec,dist)

######################################################################
def mjd_moon_alt(alt,mjdguess,lat,long,elevsea):
    """ returns jd at which moon is at a given
        altitude, given jdguess as a starting point. In current version
        uses high-precision moon -- execution time does not seem to be
        excessive on modern hardware.  If it's a problem on your machine,
        you can replace calls to 'accumoon' with 'lpmoon' and remove
        the 'elevsea' argument.

        returns (geora,geodec,geodist,topora,topodec,topodist)

        from skycalcv5
        """

    dl=2e-3
    i=0
    
    sid=utc_lmst(mjdguess,long)    
    [geora,geodec,geodist,ra,dec,dist]=accumoon(mjdguess,lat,sid,elevsea)
    ha=utc_lmst(mjdguess,long)-ra
    [alt2,az,par]=altit(dec,ha,lat)
    mjdguess=mjdguess+dl
    sid=utc_lmst(mjdguess,long)    
    [geora,geodec,geodist,ra,dec,dist]=accumoon(mjdguess,lat,sid,elevsea)
    [alt3,az,par]=altit(dec,sid-ra,lat)
    err=alt3-alt
    deriv=(alt3-alt2)/dl
    while (math.fabs(err)>.1 and i < 10):
        mjdguess-=err/deriv
        sid=utc_lmst(mjdguess,long)
        [geora,geodec,geodist,ra,dec,dist]=accumoon(mjdguess,lat,sid,elevsea)
        [alt3,az,par]=altit(dec,sid-ra,lat)
        err=alt3-alt
        i+=1
        if (i==9):
            printerr("Moon rise/set not converging\n")
    if (i>=9):
        mjdguess=-1e3
    return mjdguess    

######################################################################
def accumoon(mjd,geolat,lst,elevsea):
    """
    mjd, dec. degr., dec. hrs., meters
    More accurate (but more elaborate and slower) lunar
    ephemeris, from Jean Meeus' *Astronomical Formulae For Calculators*,
    pub. Willman-Bell.  Includes all the terms given there.

    from skycalcv5
    """

    jd=mjd+2400000.5
    # approx correction to ephem
    jd+=etcorr(mjd)/SEC_IN_DAY
    # based around 1900
    T=(jd-2415020)/36525
    Tsq=T*T
    Tcb=Tsq*T

    Lpr = 270.434164 + 481267.8831 * T - 0.001133 * Tsq + 0.0000019 * Tcb
    M = 358.475833 + 35999.0498*T - 0.000150*Tsq - 0.0000033*Tcb
    Mpr = 296.104608 + 477198.8491*T + 0.009192*Tsq + 0.0000144*Tcb
    D = 350.737486 + 445267.1142*T - 0.001436 * Tsq + 0.0000019*Tcb
    F = 11.250889 + 483202.0251*T -0.003211 * Tsq - 0.0000003*Tcb
    Om = 259.183275 - 1934.1420*T + 0.002078*Tsq + 0.0000022*Tcb
    Lpr = circulo(Lpr)
    Mpr = circulo(Mpr)
    M = circulo(M)
    D = circulo(D)
    F = circulo(F)
    Om = circulo(Om)

    sinx =  math.sin((51.2 + 20.2 * T)/DEG_IN_RADIAN)
    Lpr = Lpr + 0.000233 * sinx
    M = M - 0.001778 * sinx
    Mpr = Mpr + 0.000817 * sinx
    D = D + 0.002011 * sinx
    
    sinx = 0.003964 * math.sin((346.560+132.870*T -0.0091731*Tsq)/DEG_IN_RADIAN)
    
    Lpr = Lpr + sinx
    Mpr = Mpr + sinx
    D = D + sinx
    F = F + sinx

    sinx = math.sin(Om/DEG_IN_RADIAN)
    Lpr = Lpr + 0.001964 * sinx
    Mpr = Mpr + 0.002541 * sinx
    D = D + 0.001964 * sinx
    F = F - 0.024691 * sinx
    F = F - 0.004328 * math.sin((Om + 275.05 -2.30*T)/DEG_IN_RADIAN)
    
    e = 1 - 0.002495 * T - 0.00000752 * Tsq
    
    # these will all be arguments ... 
    M = M / DEG_IN_RADIAN   
    Mpr = Mpr / DEG_IN_RADIAN
    D = D / DEG_IN_RADIAN
    F = F / DEG_IN_RADIAN

    lmbda = Lpr + 6.288750*math.sin(Mpr)+ 1.274018*math.sin(2*D - Mpr)+ 0.658309*math.sin(2*D)+ 0.213616*math.sin(2*Mpr)- e*0.185596*math.sin(M)- 0.114336*math.sin(2*F)+ 0.058793*math.sin(2*D - 2*Mpr)+ e*0.057212*math.sin(2*D - M - Mpr)+ 0.053320*math.sin(2*D + Mpr)+ e*0.045874*math.sin(2*D - M)+ e*0.041024*math.sin(Mpr - M)- 0.034718*math.sin(D)
    lmbda+=- e*0.030465*math.sin(M+Mpr)+ 0.015326*math.sin(2*D - 2*F)- 0.012528*math.sin(2*F + Mpr)- 0.010980*math.sin(2*F - Mpr)+ 0.010674*math.sin(4*D - Mpr)+ 0.010034*math.sin(3*Mpr)+ 0.008548*math.sin(4*D - 2*Mpr)- e*0.007910*math.sin(M - Mpr + 2*D)- e*0.006783*math.sin(2*D + M)+ 0.005162*math.sin(Mpr - D)
    lmbda+=e*0.005000*math.sin(M + D)+ e*0.004049*math.sin(Mpr - M + 2*D)+ 0.003996*math.sin(2*Mpr + 2*D)+ 0.003862*math.sin(4*D)+ 0.003665*math.sin(2*D - 3*Mpr)+ e*0.002695*math.sin(2*Mpr - M)+ 0.002602*math.sin(Mpr - 2*F - 2*D)+ e*0.002396*math.sin(2*D - M - 2*Mpr)- 0.002349*math.sin(Mpr + D)+ e*e*0.002249*math.sin(2*D - 2*M)- e*0.002125*math.sin(2*Mpr + M)- e*e*0.002079*math.sin(2*M)+ e*e*0.002059*math.sin(2*D - Mpr - 2*M)- 0.001773*math.sin(Mpr + 2*D - 2*F)- 0.001595*math.sin(2*F + 2*D)
    lmbda+= e*0.001220*math.sin(4*D - M - Mpr)- 0.001110*math.sin(2*Mpr + 2*F)+ 0.000892*math.sin(Mpr - 3*D)- e*0.000811*math.sin(M + Mpr + 2*D)+ e*0.000761*math.sin(4*D - M - 2*Mpr)+ e*e*0.000717*math.sin(Mpr - 2*M)+ e*e*0.000704*math.sin(Mpr - 2*M - 2*D)+ e*0.000693*math.sin(M - 2*Mpr + 2*D)+ e*0.000598*math.sin(2*D - M - 2*F)+ 0.000550*math.sin(Mpr + 4*D)+ 0.000538*math.sin(4*Mpr)+ e*0.000521*math.sin(4*D - M)+ 0.000486*math.sin(2*Mpr - D)

    B = 5.128189*math.sin(F)+ 0.280606*math.sin(Mpr + F)+ 0.277693*math.sin(Mpr - F)+ 0.173238*math.sin(2*D - F)+ 0.055413*math.sin(2*D + F - Mpr)+ 0.046272*math.sin(2*D - F - Mpr)+ 0.032573*math.sin(2*D + F)+ 0.017198*math.sin(2*Mpr + F)+ 0.009267*math.sin(2*D + Mpr - F)+ 0.008823*math.sin(2*Mpr - F)+ e*0.008247*math.sin(2*D - M - F)+ 0.004323*math.sin(2*D - F - 2*Mpr)+ 0.004200*math.sin(2*D + F + Mpr)+ e*0.003372*math.sin(F - M - 2*D)+ 0.002472*math.sin(2*D + F - M - Mpr)+ e*0.002222*math.sin(2*D + F - M)+ e*0.002072*math.sin(2*D - F - M - Mpr)+ e*0.001877*math.sin(F - M + Mpr)+ 0.001828*math.sin(4*D - F - Mpr)- e*0.001803*math.sin(F + M)- 0.001750*math.sin(3*F)+ e*0.001570*math.sin(Mpr - M - F)- 0.001487*math.sin(F + D)- e*0.001481*math.sin(F + M + Mpr)+ e*0.001417*math.sin(F - M - Mpr)+ e*0.001350*math.sin(F - M)+ 0.001330*math.sin(F - D)+ 0.001106*math.sin(F + 3*Mpr)+ 0.001020*math.sin(4*D - F)+ 0.000833*math.sin(F + 4*D - Mpr)
    B+=0.000781*math.sin(Mpr - 3*F)+ 0.000670*math.sin(F + 4*D - 2*Mpr)+ 0.000606*math.sin(2*D - 3*F)+ 0.000597*math.sin(2*D + 2*Mpr - F)+ e*0.000492*math.sin(2*D + Mpr - M - F)+ 0.000450*math.sin(2*Mpr - F - 2*D)+ 0.000439*math.sin(3*Mpr - F)+ 0.000423*math.sin(F + 2*D + 2*Mpr)+ 0.000422*math.sin(2*D - F - 3*Mpr)- e*0.000367*math.sin(M + F + 2*D - Mpr)- e*0.000353*math.sin(M + F + 2*D)+ 0.000331*math.sin(F + 4*D)+ e*0.000317*math.sin(2*D + F - M + Mpr)+ e*e*0.000306*math.sin(2*D - 2*M - F)- 0.000283*math.sin(Mpr + 3*F)

    om1 = 0.0004664 * math.cos(Om/DEG_IN_RADIAN)
    om2 = 0.0000754 * math.cos((Om + 275.05 - 2.30*T)/DEG_IN_RADIAN)

    beta = B * (1. - om1 - om2)

    pie = 0.950724+ 0.051818 * math.cos(Mpr)+ 0.009531 * math.cos(2*D - Mpr)+ 0.007843 * math.cos(2*D)+ 0.002824 * math.cos(2*Mpr)+ 0.000857 * math.cos(2*D + Mpr)+ e * 0.000533 * math.cos(2*D - M)+ e * 0.000401 * math.cos(2*D - M - Mpr)+ e * 0.000320 * math.cos(Mpr - M)- 0.000271 * math.cos(D)- e * 0.000264 * math.cos(M + Mpr)- 0.000198 * math.cos(2*F - Mpr)+ 0.000173 * math.cos(3*Mpr)+ 0.000167 * math.cos(4*D - Mpr)- e * 0.000111 * math.cos(M)+ 0.000103 * math.cos(4*D - 2*Mpr)- 0.000084 * math.cos(2*Mpr - 2*D)- e * 0.000083 * math.cos(2*D + M)+ 0.000079 * math.cos(2*D + 2*Mpr)+ 0.000072 * math.cos(4*D)+ e * 0.000064 * math.cos(2*D - M + Mpr)- e * 0.000063 * math.cos(2*D + M - Mpr)+ e * 0.000041 * math.cos(M + D)+ e * 0.000035 * math.cos(2*Mpr - M)- 0.000033 * math.cos(3*Mpr - 2*D)- 0.000030 * math.cos(Mpr + D)- 0.000029 * math.cos(2*F - 2*D)- e * 0.000029 * math.cos(2*Mpr + M)+ e * e * 0.000026 * math.cos(2*D - 2*M)- 0.000023 * math.cos(2*F - 2*D + Mpr)+ e * 0.000019 * math.cos(4*D - M - Mpr)
    
    beta = beta/DEG_IN_RADIAN
    lmbda = lmbda/DEG_IN_RADIAN
    l = math.cos(lmbda) * math.cos(beta)
    m = math.sin(lmbda) * math.cos(beta)
    n = math.sin(beta)
    [l,m,n]=eclrot(mjd,l,m,n)
    
    dist = 1/math.sin((pie)/DEG_IN_RADIAN)
    x = l * dist
    y = m * dist
    z = n * dist
    
    geora=math.atan2(m,l)*HRS_IN_RADIAN
    geora=putrange(geora)
    geodec=math.asin(n)*DEG_IN_RADIAN
    geodist=dist
    
    [x_geo,y_geo,z_geo]=geocent(lst,geolat,elevsea)

    # topocentric correction using elliptical earth fig.
    x-=x_geo
    y-=y_geo
    z-=z_geo
    
    topodist=math.sqrt(x*x+y*y+z*z)
    l=x/topodist
    m=y/topodist
    n=z/topodist
    
    topora=math.atan2(m,l)*HRS_IN_RADIAN
    topora=putrange(topora)
    topodec=math.asin(n)*DEG_IN_RADIAN

    return (geora,geodec,geodist,topora,topodec,topodist)


######################################################################
# Sun routines
######################################################################

######################################################################
def lpsun(mjd):
    """
    Low precision formulae for the sun, from Almanac p. C24 (1990) 
    ra and dec are returned as decimal hours and decimal degrees.
    outputs ra,dec in decimal hours,degrees

    from skycalcv5
    """

    n = mjd - J2000
    L = 280.460 + 0.9856474 * n
    g = (357.528 + 0.9856003 * n)/DEG_IN_RADIAN
    lmbda = (L + 1.915 * math.sin(g) + 0.020 * math.sin(2. * g))/DEG_IN_RADIAN
    epsilon = (23.439 - 0.0000004 * n)/DEG_IN_RADIAN

    x = math.cos(lmbda)
    y = math.cos(epsilon) * math.sin(lmbda)
    z = math.sin(epsilon)*math.sin(lmbda)

    ra=math.atan2(y,x)
    ra=putrange(ra,2*math.pi)

    ra*=HRS_IN_RADIAN
    dec=math.asin(z)*DEG_IN_RADIAN
    return (ra,dec)


######################################################################
def mjd_sun_alt(alt,mjdguess,lat,long):
    """ returns jd at which sun is at a given
    altitude, given jdguess as a starting point. Uses
    low-precision sun, which is plenty good enough.
    
    from skycalcv5
    """

    dl=2e-3

    i=0
    # first guess
    [ra,dec]=lpsun(mjdguess)
    ha=utc_lmst(mjdguess,long)-ra
    [alt2,az,par]=altit(dec,ha,lat)
    mjdguess+=dl
    [ra,dec]=lpsun(mjdguess)
    [alt3,az,par]=altit(dec,utc_lmst(mjdguess,long)-ra,lat)
    err=alt3-alt
    deriv=(alt3-alt2)/dl
    while (math.fabs(err)>0.1 and i<10):
        mjdguess-=err/deriv
        [ra,dec]=lpsun(mjdguess)
        [alt3,az,par]=altit(dec,utc_lmst(mjdguess,long)-ra,lat)
        err=alt3-alt
        i+=1
        if (i==9):
            printerr("Sunrise, set or twilight calculation not converging!\n")
    if (i>=9):
        mjdguess=-1e3

    mjdout=mjdguess
    return mjdout

######################################################################
# Airmass/Ephemeris routines
######################################################################

######################################################################
def get_amlimit(obj,tm,mjd,amlim=2.0):

    tmin=tm.LT-8
    tmax=tm.LT+8
    dt=0.125

    t=tmin
    tm.LT=t
    am=get_airmass(obj.ra,obj.dec,tm.obs.lat,tm.obs.long,tm.MJD+tm.UT/24.0)
    if (am>amlim or am<0):
        isgtr=1
    else:
        isgtr=0
    T=[]
    AM=[]
    i1=[]
    i2=[]
    i=0
    while (t<=tmax):
        tm.LT=t
        am=get_airmass(obj.ra,obj.dec,tm.obs.lat,tm.obs.long,tm.MJD+tm.UT/24.0)
        if (isgtr and (am<amlim) and not (am<0)):
            isgtr=0
            i1.append(i-1)
            i2.append(i)
        if (not isgtr and (am>amlim) and not (am<0)):
            isgtr=1
            i1.append(i-1)
            i2.append(i)
        
        T.append(t)
        AM.append(am)            
        t+=dt
        i+=1

    Tlim=[]
    for i in range(0,len(i1)):
        Tlim.append(interp1([AM[i1[i]],AM[i2[i]]],[T[i1[i]],T[i2[i]]],amlim))
        
    return Tlim    
        
    
######################################################################
def print_amtable(obj,tm,tmin,tmax,dt,isut=1):
    """prints an airmass table for the Object obj
    with the Time/Observatory in tm
    at mjd, from tmin..tmax with interval dt (UT if isut, else LT)
    also returns the full string
    """


    moon=Moon(tm)    
    [yr,mn,dy]=mjd_cal(tm.MJD)    
    s=''
    s+='Midnight: MJD %.1f %s %d-%02d-%02d %s UT=%s LST\n' % (tm.MJD+tm.utmlt/24.0,dow[day_of_week(tm.MJD)],yr,mn,dy,dec2sexstring(tm.UT,digits=0),dec2sexstring(tm.LST,digits=0))
    if (obj != None):
        [rout,dout]=precess(obj,tm)
        obj_moon = DEG_IN_RADIAN * obj.angulardistance(moon.obj)

        s+="%s\n" % obj
        s+="\t(%s,%s) (%.2f)\n" % (dec2sexstring(rout),dec2sexstring(dout,1,digits=1),tm.epoch)
        s+="\t%.1f deg. from moon\n\n" % obj_moon
        s+="%s\t\tUT\t\tLST\t\tAM\tAlt\tParAng\tMoonAlt\tSunAlt\n" % tm.LTtype
    
        [LT,UT,LST,AM,Alt,Par,AltMoon,AltSun]=calc_amtable(obj,tm,tmin,tmax,dt,isut)
    
        for i in range(0,len(AM)):
            s+="%s\t%s\t%s\t%.2f\t%02d.%d\t%04d.%d\t%03d.%d\t%03d.%d\n" % (dec2sexstring(LT[i],digits=0),dec2sexstring(UT[i],digits=0),dec2sexstring(LST[i],digits=0),AM[i],int(Alt[i]),frac(Alt[i])*10,int(Par[i]),frac(abs(Par[i]))*10,int(AltMoon[i]),frac(abs(AltMoon[i]))*10,int(AltSun[i]),frac(abs(AltSun[i]))*10)
    print s
    return s

######################################################################
def calc_amtable(obj,tm,tmin,tmax,dt,isut=1):
    """calculatess an airmass table for the Object obj
    with the Time/Observatory in tm
    at mjd, from tmin..tmax with interval dt (UT if isut, else LT)
    """

    t=tmin
    [yr,mn,dy]=mjd_cal(tm.MJD)

    LT=[]
    UT=[]
    LST=[]
    AM=[]
    Alt=[]
    Par=[]
    AltMoon=[]
    AltSun=[]
    while (t<=tmax):
        if (isut):
            tm.UT=t
        else:
            tm.LT=t
        am=get_airmass(obj.ra,obj.dec,tm.obs.lat,tm.obs.long,tm.MJD+tm.UT/24.0)
        localmoon=Moon(tm)
        localsun=Sun(tm)
        [altmoon,azmoon,parmoon]=altit(localmoon.obj.dec,localmoon.obj.ra-tm.LST,tm.obs.lat)
        [altsun,azsun,parsun]=altit(localsun.obj.dec,localsun.obj.ra-tm.LST,tm.obs.lat)
        LT.append(tm.LT)
        UT.append(tm.UT)
        LST.append(tm.LST)
        if (am>=1 and am<10):
            AM.append(am)
        else:
            AM.append(9.99)
        [alt,az,par]=altit(obj.dec,obj.ra-tm.LST,tm.obs.lat)
        if (alt>0):
            Alt.append(alt)
            Par.append(par)
        else:
            Alt.append(0)
            Par.append(0)
        if (altmoon >= 0):
            AltMoon.append(altmoon)
        else:
            AltMoon.append(0)
        if (altsun >= -20):
            AltSun.append(altsun)
        else:
            AltSun.append(0)

        t+=dt

    return (LT,UT,LST,AM,Alt,Par,AltMoon,AltSun)

######################################################################
# COORDINATE ROUTINES
######################################################################

######################################################################
def pyephem_altaz(ra,dec,lat,long,ut):
    """
    [alt,az]=pyephem_altaz(ra,dec,lat,long,ut)
    
    based on routines in pyephem
    ra in hours
    dec in degrees
    lat,long in degrees
    ut in MJD

    azimuth is defined so that N=0 deg
    """
    observer=ephem.Observer()
    # make sure no refraction is included
    observer.pressure=0
    mwa=Obs[obscode['MWA']]
    observer.long=mwa.long/DEG_IN_RADIAN
    observer.lat=mwa.lat/DEG_IN_RADIAN
    observer.elevation=mwa.elev
    mjd=int(ut)
    ut=24*(ut-mjd)
    [yr,mn,dy]=mjd_cal(mjd)
    time=dec2sexstring(ut)
    observer.date='%d/%d/%d %s' % (yr,mn,dy,time)
    src=ephem.readdb("%s,f|J,%s,%s,0.00,2000.0,0" % ("test",ra,dec))
    src.compute(observer)
    return (src.alt*DEG_IN_RADIAN,src.az*DEG_IN_RADIAN)



######################################################################
def altaz(ra,dec,lat,long,ut):
    """
    [alt,az]=altaz(ra,dec,lat,long,ut)
    
    from S&T WWW page (ALTAZ.BAS)
    ra in hours
    dec in degrees
    lat,long in degrees
    ut in MJD

    azimuth is defined so that N=0 deg

    will accept numpy.ndarray as ra,dec
    """

    if (not isinstance(ra,numpy.ndarray)):
        r1=math.pi/180
        lmst=utc_lmst(ut,long)*15*r1
        ra=checksex(ra)*15*r1
        dec=checksex(dec)*r1
        lat=checksex(lat)*r1
        long=checksex(long)*r1
        
        t5=lmst-ra
        s1=math.sin(lat)*math.sin(dec)
        s1+=math.cos(lat)*math.cos(dec)*math.cos(t5)
        c1=1-s1*s1
        if (c1>0):
            c1=math.sqrt(c1)
            h=math.atan2(s1,c1)
        else:
            if (s1>=0):
                h=math.pi/2
            else:
                h=-math.pi/2
        c2=math.cos(lat)*math.sin(dec)
        c2-=math.sin(lat)*math.cos(dec)*math.cos(t5)
        s2=-math.cos(dec)*math.sin(t5)
        if (c2 != 0):
            a=math.atan2(s2,c2)
            if (c2<0):
                a+=math.pi
        else:
            a=math.pi/2
            if (s2<0):
                a*=-1
        if (a<0):
            a+=math.pi*2
        alt=h/r1
        az=a/r1
        return (alt,az)
    else:

        # numpy version
        #alt=numpy.ndarray(ra.shape)
        #az=numpy.ndarray(ra.shape)
        #for i in xrange(len(ra)):
        #    [alt[i],az[i]]=altaz(ra[i],dec[i],lat,long,ut)
        #return (alt,az)
        r1=math.pi/180
        lmst=utc_lmst(ut,long)*15*r1
        ra=(ra)*15*r1
        dec=(dec)*r1
        lat=(lat)*r1
        long=(long)*r1
        
        t5=lmst-ra
        s1=math.sin(lat)*numpy.sin(dec)
        s1+=math.cos(lat)*numpy.cos(dec)*numpy.cos(t5)
        c1=1-s1*s1
        i=numpy.where(c1>0)[0]
        h=numpy.zeros(ra.shape)
        a=numpy.zeros(ra.shape)
        if (len(i)>0):
            c1[i]=numpy.sqrt(c1[i])            
            h[i]=numpy.arctan2(s1[i],c1[i])
        i=numpy.where(c1==0)[0]
        if (len(i)>0):
            ipos=numpy.where(s1[i]>=0)[0]
            ineg=numpy.where(s1[i]<0)[0]
            if (len(ipos)>0):
                h[i[ipos]]=math.pi/2
            if (len(ineg)>0):
                h[i[ineg]]=-math.pi/2
        c2=math.cos(lat)*numpy.sin(dec)
        c2-=math.sin(lat)*numpy.cos(dec)*numpy.cos(t5)
        s2=-numpy.cos(dec)*numpy.sin(t5)
        i=numpy.where(c2 != 0)[0]
        if (len(i)>0):
            a[i]=numpy.arctan2(s2[i],c2[i])
        i=numpy.where(c2<0)[0]
        a[i]+=math.pi
        i=numpy.where(c2==0)[0]
        if (len(i)>0):
            a[i]=math.pi/2
            ineg=numpy.where(s2[i]<0)[0]
            a[i[ineg]]*=-1
        a[numpy.where(a<0)]+=math.pi*2
        alt=h/r1
        az=a/r1
        return (alt,az)


######################################################################
def get_airmass(ra,dec,lat,long,ut):

    """
    airmass=get_airmass(ra,dec,lat,long,ut)
    
    ra in hours
    dec in degrees
    lat,long in degrees
    ut in MJD

    will accept numpy.ndarray as ra,dec
    """

    [alt,az]=altaz(ra,dec,lat,long,ut)
    za=90.0-alt
    if (not isinstance(ra,numpy.ndarray)):
        am=1.0/math.cos(za*math.pi/180)
    else:
        am=1.0/numpy.cos(za*math.pi/180)
        
    return am

######################################################################
def precess(obj,tm,from_std=1):
    """ General routine for precession and apparent place. Either
      transforms from current epoch (given by fractional years) to a standard
      epoch or back again, depending on value of the switch
      'from_std'; 1 transforms from standard to current, -1 goes
      the other way.

      Precession uses a matrix procedures as outlined in Taff's
      Computational Spherical Astronomy book.  This is the so-called
      'rigorous' method which should give very accurate answers all
      over the sky over an interval of several centuries.  Naked eye
      accuracy holds to ancient times, too.  Precession constants used
      are the new IAU1976 -- the 'J2000' system.

      from skycalcv5
      """

    rin=obj.ra
    din=obj.dec
    Std_epoch=obj.epoch
    if (isinstance(Std_epoch,str)):
        if (Std_epoch.find('J')>=0):
            Std_epoch=(Std_epoch.replace('J',''))

        std_epoch=float(Std_epoch)
    else:
        std_epoch=Std_epoch
        
    date_epoch=mjd_to_epoch(tm.MJD)

    # rotation matrix
    p=numarray.array(shape=[4,4],type='Float32')
    # inversion
    t=numarray.array(shape=[4,4],type='Float32')
    # original unit vector
    orig=numarray.array(shape=[4],type='Float32')
    # final vector
    fin=numarray.array(shape=[4],type='Float32')

    ti=(std_epoch-2000.0)/100
    tf=(date_epoch-2000.-100.*ti)/100
    zeta = (2306.2181 + 1.39656 * ti + 0.000139 * ti * ti) * tf 
    zeta+=(0.30188 - 0.000344 * ti) * tf * tf + 0.017998 * tf * tf * tf
    z = zeta + (0.79280 + 0.000410 * ti) * tf * tf + 0.000205 * tf * tf * tf
    theta = (2004.3109 - 0.8533 * ti - 0.000217 * ti * ti) * tf
    theta-= (0.42665 + 0.000217 * ti) * tf * tf - 0.041833 * tf * tf * tf

    # convert to radians
    ARCSEC_IN_RADIANS=206264.80625
    zeta/=ARCSEC_IN_RADIANS
    z/=ARCSEC_IN_RADIANS
    theta/=ARCSEC_IN_RADIANS

    # trig functions
    cosz=math.cos(z)
    coszeta=math.cos(zeta)
    costheta=math.cos(theta)
    sinz=math.sin(z)
    sinzeta=math.sin(zeta)
    sintheta=math.sin(theta)

    # compute elements of precession matrix: from standard to input */
    p[1,1]=coszeta*cosz*costheta-sinzeta*sinz
    p[1,2]=-sinzeta*cosz*costheta-coszeta*sinz
    p[1,3]=-cosz*sintheta

    p[2,1] = coszeta * sinz * costheta + sinzeta * cosz;
    p[2,2] = -1. * sinzeta * sinz * costheta + coszeta * cosz;
    p[2,3] = -1. * sinz * sintheta;
    
    p[3,1] = coszeta * sintheta;
    p[3,2] = -1. * sinzeta * sintheta;
    p[3,3] = costheta;

    if (from_std):
        r=p
    else:
        # inverse is transpose
        for i in range(1,4):
            for j in range(1,4):
                t[i,j]=p[j,i]
        r=t

    # transform coords
    radian_ra=15*rin*math.pi/180
    radian_dec=din*math.pi/180

    orig[1]=math.cos(radian_dec)*math.cos(radian_ra)
    orig[2]=math.cos(radian_dec)*math.sin(radian_ra)
    orig[3]=math.sin(radian_dec)
    for i in range(1,4):
        fin[i]=0
        for j in range(1,4):
            fin[i]+=r[i,j]*orig[j]

    # convert back to spherical
    [rout,dout]=xyz_cel(fin[1],fin[2],fin[3])
    return (rout,dout)

######################################################################
def xyz_cel(x,y,z):
    """ cartesian coordinate triplet 
    returns corresponding right ascension and declination,
    in decimal hours & degrees.
    """

    mod=math.sqrt(x*x+y*y+z*z)
    if (mod>0):
        x/=mod
        y/=mod
        z/=mod
    else:
        return (0,0)
    xy=math.sqrt(x*x+y*y)
    if (xy<1e-11):
        # on the pole
        ra=0
        dec=math.pi/2
        if (z<0):
            z*=-1
    else:
        dec=math.asin(z)
        ra=math.atan2(y,x)

    ra*=(180/math.pi)/15
    ra=putrange(ra)
    dec*=180/math.pi

    return (ra,dec)    

######################################################################
def angulardistance(ra1,dec1,ra2,dec2):
    """ input in decimal hours,degrees
    angle separating by two positions in the sky --
    return value is in radians.  Hybrid algorithm works down
    to zero separation except very near the poles.
    
    from skycalcv5"""

    if (not isinstance(ra1,numpy.ndarray) and not isinstance(dec1,numpy.ndarray) and not isinstance(ra2,numpy.ndarray) and not isinstance(dec2,numpy.ndarray)):
        ra1 = ra1 / HRS_IN_RADIAN
        dec1 = dec1 / DEG_IN_RADIAN
        ra2 = ra2 / HRS_IN_RADIAN
        dec2 = dec2 / DEG_IN_RADIAN
        x1 = math.cos(ra1)*math.cos(dec1)
        y1 = math.sin(ra1)*math.cos(dec1)
        z1 = math.sin(dec1)
        x2 = math.cos(ra2)*math.cos(dec2)
        y2 = math.sin(ra2)*math.cos(dec2)
        z2 = math.sin(dec2)
        arg=x1*x2+y1*y2+z1*z2
        if (arg>1):
            arg=1
        if (arg<-1):
            arg=-1
        theta = math.acos(arg)
        # use flat Pythagorean approximation if the angle is very small
        # *and* you're not close to the pole; avoids roundoff in arccos.
        if (theta<1e-5):
            if (math.fabs(dec1)<(math.pi/2-1e-3) and (math.fabs(dec2)<math.pi/2-1e-3)):
                x1=(ra2-ra1)*math.cos(0.5*(dec1+dec2))
                x2=dec2-dec1
                theta=math.sqrt(x1*x1+x2*x2)
        return theta
    else:
        # numpy version
        # promote all elements as necessary
        ra1 = numpy.array(ra1) / HRS_IN_RADIAN
        dec1 = numpy.array(dec1) / DEG_IN_RADIAN
        ra2 = numpy.array(ra2) / HRS_IN_RADIAN
        dec2 = numpy.array(dec2) / DEG_IN_RADIAN
        x1 = numpy.cos(ra1)*numpy.cos(dec1)
        y1 = numpy.sin(ra1)*numpy.cos(dec1)
        z1 = numpy.sin(dec1)
        x2 = numpy.cos(ra2)*numpy.cos(dec2)
        y2 = numpy.sin(ra2)*numpy.cos(dec2)
        z2 = numpy.sin(dec2)
        arg=x1*x2+y1*y2+z1*z2
        arg[arg>1]=1
        arg[arg<-1]=-1
        theta = numpy.arccos(arg)
        x1=(ra2-ra1)*numpy.cos(0.5*(dec1+dec2))
        x2=dec2-dec1
        theta2=numpy.sqrt(x1*x1+x2*x2)

        # use flat Pythagorean approximation if the angle is very small
        # *and* you're not close to the pole; avoids roundoff in arccos.
        condition=(theta<1e-5)*(numpy.abs(dec1)<(math.pi/2-1e-3))*(numpy.abs(dec2)<(math.pi/2-1e-3))
        d=numpy.where(condition,theta2,theta)

        #for i in xrange(len(self)):
        #    d[i]=self[i].distance(obj)
        return d

######################################################################
def altit(dec,ha,lat):
    """
    returns altitude(degr) for dec, ha, lat (decimal degr, hr, degr);
    also computes and returns azimuth
    and as an extra added bonus returns parallactic angle (decimal degr)

    azimuth is defined so that E=0 deg

    now supports numpy.ndarray as arguments

    from skycalcv5
    """

    parang2=calc_parang(ha,dec,lat)
    if (isinstance(dec,float) or isinstance(dec,int)):
        dec/=DEG_IN_RADIAN
        ha/=HRS_IN_RADIAN
        lat/=DEG_IN_RADIAN
        
        cosdec=math.cos(dec)
        sindec=math.sin(dec)
        cosha=math.cos(ha)
        sinha=math.sin(ha)
        coslat=math.cos(lat)
        sinlat=math.sin(lat)
        
        x=DEG_IN_RADIAN*math.asin(cosdec*cosha*coslat+sindec*sinlat)
        # component due N
        y=sindec*coslat-cosdec*cosha*sinlat
        # comp. due E
        z=-cosdec*sinha
        az=math.atan2(y,z)
        
        # as it turns out, having knowledge of the altitude and
        # azimuth makes the spherical trig of the parallactic angle
        # less ambiguous ... so do it here!  Method uses the
        # "astronomical triangle" connecting celestial pole, object,
        # and zenith ... now know all the other sides and angles,
        # so we can crush it ...
        
        if (cosdec != 0):
            sinp=-math.sin(az)*coslat/cosdec
            cosp=-math.cos(az)*cosha-math.sin(az)*sinha*sinlat
            #parang=math.atan2(cosp,sinp)*DEG_IN_RADIAN
            parang=math.atan2(sinp,cosp)*DEG_IN_RADIAN        
        else:
            if (lat>=0):
                parang=180
            else:
                parang=0
        az*=DEG_IN_RADIAN
        az=putrange(az,360)

        return (x,az,-parang2)

    elif (isinstance(dec,numpy.ndarray)):
        # numpy version
        decuse=dec/DEG_IN_RADIAN
        hause=ha/HRS_IN_RADIAN
        latuse=lat/DEG_IN_RADIAN
        
        cosdec=numpy.cos(decuse)
        sindec=numpy.sin(decuse)
        cosha=numpy.cos(hause)
        sinha=numpy.sin(hause)
        coslat=numpy.cos(latuse)
        sinlat=numpy.sin(latuse)

        x=DEG_IN_RADIAN*numpy.arcsin(cosdec*cosha*coslat+sindec*sinlat)
        # component due N
        y=sindec*coslat-cosdec*cosha*sinlat
        # comp. due E
        z=-cosdec*sinha
        az=numpy.arctan2(y,z)

        # as it turns out, having knowledge of the altitude and
        # azimuth makes the spherical trig of the parallactic angle
        # less ambiguous ... so do it here!  Method uses the
        # "astronomical triangle" connecting celestial pole, object,
        # and zenith ... now know all the other sides and angles,
        # so we can crush it ...
        
        cosdecnozero=cosdec
        cosdecnozero[cosdec==0]=1
        sinp=-numpy.sin(az)*coslat/cosdecnozero
        cosp=-numpy.cos(az)*cosha-numpy.sin(az)*sinha*sinlat
        parang=numpy.arctan2(sinp,cosp)*DEG_IN_RADIAN        
        if (numpy.any(cosdec==0)):
            parang[(cosdec==0)*(lat>0)]=180
            parang[(cosdec==0)*(lat<=0)]=0
                
        az*=DEG_IN_RADIAN
        az=putrange(az,360)

        return (x,az,-parang2)
    else:
        raise TypeError

######################################################################
def azel2radec(Az,El,gpstime):
    """
    [RA,Dec]=azel2radec(Az,El,gpstime)
    horizon coords to equatorial
    all decimal degrees
    The sign convention for azimuth is north zero, east +pi/2.
    positions are J2000
    """

    mwa=Obs[obscode['MWA']]
    [MJD,UT]=calcUTGPSseconds(gpstime)
    [yr,mn,dy]=mjd_cal(MJD)
    UTs=dec2sexstring(UT,digits=0,roundseconds=1)
    observer=ephem.Observer()
    # make sure no refraction is included
    observer.pressure=0
    observer.long=mwa.long/DEG_IN_RADIAN
    observer.lat=mwa.lat/DEG_IN_RADIAN
    observer.elevation=mwa.elev
    observer.date='%d/%d/%d %s' % (yr,mn,dy,UTs)

    ra,dec=observer.radec_of(Az/DEG_IN_RADIAN,El/DEG_IN_RADIAN)
    return ra*DEG_IN_RADIAN,dec*DEG_IN_RADIAN

######################################################################
def radec2azel(RA,Dec,gpstime):
    """
    Az,El=radec2azel(RA,Dec,gpstime)
    equatorial to horizon coords 
    all decimal degrees
    The sign convention for azimuth is north zero, east +pi/2.
    positions are J2000
    """

    mwa=Obs[obscode['MWA']]
    [MJD,UT]=calcUTGPSseconds(gpstime)
    [yr,mn,dy]=mjd_cal(MJD)
    UTs=dec2sexstring(UT,digits=0,roundseconds=1)
    observer=ephem.Observer()
    # make sure no refraction is included
    observer.pressure=0
    observer.long=mwa.long/DEG_IN_RADIAN
    observer.lat=mwa.lat/DEG_IN_RADIAN
    observer.elevation=mwa.elev
    observer.date='%d/%d/%d %s' % (yr,mn,dy,UTs)

    body=ephem.FixedBody()
    body._ra=RA/DEG_IN_RADIAN
    body._dec=Dec/DEG_IN_RADIAN
    body.compute(observer)

    return body.az*DEG_IN_RADIAN,body.alt*DEG_IN_RADIAN

######################################################################
def horz2eq(Az,El,lat):
    """
    [HA,Dec]=horz2eq(Az,El,lat)
    horizon coords to equatorial
    all decimal degrees
    The sign convention for azimuth is north zero, east +pi/2.
    from slalib sla_h2e
    https://starlink.jach.hawaii.edu/viewvc/trunk/libraries/sla/h2e.f?view=markup
    """

    if (isinstance(Az,numpy.ndarray)):
        sa=numpy.sin(Az*math.pi/180)
        ca=numpy.cos(Az*math.pi/180)
        se=numpy.sin(El*math.pi/180)
        ce=numpy.cos(El*math.pi/180)
        sl=numpy.sin(lat*math.pi/180)
        cl=numpy.cos(lat*math.pi/180)
        
        # HA,Dec as (x,y,z)
        x=-ca*ce*sl+se*cl
        y=-sa*ce
        z=ca*ce*cl+se*sl
        
        r=numpy.sqrt(x*x+y*y)
        ha=numpy.arctan2(y,x)
        ha[numpy.where(r==0)]=0

        dec=numpy.arctan2(z,r)

    else:
        sa=math.sin(Az*math.pi/180)
        ca=math.cos(Az*math.pi/180)
        se=math.sin(El*math.pi/180)
        ce=math.cos(El*math.pi/180)
        sl=math.sin(lat*math.pi/180)
        cl=math.cos(lat*math.pi/180)
        
        # HA,Dec as (x,y,z)
        x=-ca*ce*sl+se*cl
        y=-sa*ce
        z=ca*ce*cl+se*sl
        
        r=math.sqrt(x*x+y*y)
        if (r==0):
            ha=0
        else:
            ha=math.atan2(y,x)
        dec=math.atan2(z,r)
        
    return [ha*180/math.pi, dec*180/math.pi]
    
######################################################################
def eq2horz(HA, Dec, lat):
    """
    [Az,Alt]=eq2horz(HA,Dec,lat)
    equatorial to horizon coords
    all decimal degrees
    The sign convention for azimuth is north zero, east +pi/2.

    from slalib sla_e2h
    https://starlink.jach.hawaii.edu/viewvc/trunk/libraries/sla/e2h.f?revision=11739&view=markup
    https://starlink.jach.hawaii.edu/viewvc/trunk/libraries/sla/

    azimuth here is defined with N=0
    """
    
    if (isinstance(HA,numpy.ndarray)):
        sh=numpy.sin(HA*math.pi/180)
        ch=numpy.cos(HA*math.pi/180)
        sd=numpy.sin(Dec*math.pi/180)
        cd=numpy.cos(Dec*math.pi/180)
        sl=math.sin(lat*math.pi/180)
        cl=math.cos(lat*math.pi/180)
        
        # (Az,El) as (x,y,z)
        x=-ch*cd*sl+sd*cl
        y=-sh*cd
        z=ch*cd*cl+sd*sl
        
        # to spherical
        r=numpy.sqrt(x*x+y*y)
        a=numpy.arctan2(y,x)
        a[numpy.where(r==0)]=0
        a[numpy.where(a<0)]+=math.pi*2
        el=numpy.arctan2(z,r)
    else:
        sh=math.sin(HA*math.pi/180)
        ch=math.cos(HA*math.pi/180)
        sd=math.sin(Dec*math.pi/180)
        cd=math.cos(Dec*math.pi/180)
        sl=math.sin(lat*math.pi/180)
        cl=math.cos(lat*math.pi/180)
        
        # (Az,El) as (x,y,z)
        x=-ch*cd*sl+sd*cl
        y=-sh*cd
        z=ch*cd*cl+sd*sl
        
        # to spherical
        r=math.sqrt(x*x+y*y)
        if (r==0):
            a=0
        else:
            a=math.atan2(y,x)
        a=putrange(a,2*math.pi)
        el=math.atan2(z,r)

    return [a*180/math.pi, el*180/math.pi]

######################################################################
def calc_parang(ha,dec,lat):
    """ finds the parallactic angle.  This is a little
    complicated (see Filippenko PASP 94, 715 (1982)

    now supports numpy.ndarray as arguments, although it doesn't do it intelligently

    from skycalc
    """

    if (isinstance(ha,float) or isinstance(ha,int)):
        ha = ha / HRS_IN_RADIAN
        dec = dec / DEG_IN_RADIAN
        lat = lat / DEG_IN_RADIAN

        # Filippenko eqn 10 follows -- guarded against division by zero
        # at the exact zenith .... 
        denom =math.sqrt(1.-math.pow((math.sin(lat)*math.sin(dec)+math.cos(lat)*math.cos(dec)*math.cos(ha)),2.))
           
        if(denom != 0.):
            sineta = math.sin(ha)*math.cos(lat)/denom
        else:
            sineta = 0.
            
        if (lat >= 0.):
            # northern hemisphere case 
        
            # If you're south of zenith, no problem. 
        
            if(dec<lat):
                return (math.asin(sineta)*DEG_IN_RADIAN)

            else:
                # find critical hour angle -- where parallactic
                # angle becomes 90 deg.  After that,
                # take another root of expression. 
                colat = math.pi /2. - lat
                codec = math.pi /2. - dec
                hacrit = 1.-math.pow(math.cos(colat),2.)/math.pow(math.cos(codec),2.)
                hacrit = math.sqrt(hacrit)/math.sin(colat)
                if (abs(hacrit) <= 1.00):
                    hacrit = math.asin(hacrit)
                if (abs(ha) > abs(hacrit)):
                    # comes out ok at large hour angle */
                    return(math.asin(sineta)*DEG_IN_RADIAN)            
                else:
                    if (ha > 0):
                        return((math.pi - math.asin(sineta))*DEG_IN_RADIAN)
                    else:
                        return((-1.* math.pi - math.asin(sineta))*DEG_IN_RADIAN)
        else:
            # Southern hemisphere case follows 
            # If you're north of zenith, no problem. 
            if(dec>lat):
                if (ha >= 0):
                    return ((math.pi - math.asin(sineta))*DEG_IN_RADIAN)
                else:
                    return(-1*(math.pi + math.asin(sineta)) * DEG_IN_RADIAN)            
            else:
                # find critical hour angle -- where parallactic
                # angle becomes 90 deg.  After that,
                # take another root of expression. 
                colat = -1*math.pi/2. - lat
                codec = math.pi/2. - dec
                hacrit = 1.-math.pow(math.cos(colat),2.)/math.pow(math.cos(codec),2.)
                hacrit = math.sqrt(hacrit)/math.sin(colat)
                if (abs(hacrit) <= 1.00):
                    hacrit = math.asin(hacrit)
                if(abs(ha) > abs(hacrit)):
                    if(ha >= 0):
                        return((math.pi - math.asin(sineta))*DEG_IN_RADIAN)
                    else:
                        return(-1. * (math.pi + math.asin(sineta))*DEG_IN_RADIAN)
                else:
                    return(math.asin(sineta)*DEG_IN_RADIAN)
    elif (isinstance(ha,numpy.ndarray)):
        parang=numpy.zeros(ha.shape)
        for i in xrange(len(ha)):
            parang[i]=calc_parang(ha[i],dec[i],lat)
        return parang

    else:
        raise TypeError

           


######################################################################
def ha_alt(dec,lat,alt):
    """ returns hour angle at which object at dec is at altitude alt.
    If object is never at this altitude, signals with special
    return values 1000 (always higher) and -1000 (always lower).

    from skycalcv5
    """

    [min,max]=min_max_alt(lat,dec)
    if (alt<min):
        # always higher than asked
        return 1000
    if (alt>max):
        # always lower than asked
        return -1e3
    dec=math.pi/2-dec/DEG_IN_RADIAN
    lat=math.pi/2-lat/DEG_IN_RADIAN
    coalt=math.pi/2-alt/DEG_IN_RADIAN
    x=(math.cos(coalt)-math.cos(dec)*math.cos(lat))/(math.sin(dec)*math.sin(lat))
    if (math.fabs(x)<=1):
        return (math.acos(x)*HRS_IN_RADIAN)
    else:
        printerr("Error in ha_alt -- arccos(>1)\n")
        return 1e3
    
    
######################################################################
def min_max_alt(lat,dec):
    """ computes minimum and maximum altitude for a given dec and
    latitude.

    from skycalcv5
    """

    lat/=DEG_IN_RADIAN
    dec/=DEG_IN_RADIAN
    x=math.cos(dec)*math.cos(lat)+math.sin(dec)*math.sin(lat)
    if (math.fabs(x)<=1):
        max=math.asin(x)*DEG_IN_RADIAN
    else:
        printerr("Error in min_max_alt -- arcsin(>1)\n")
    x=math.sin(dec)*math.sin(lat)-math.cos(dec)*math.cos(lat)
    if (math.fabs(x)<=1):
        min=math.asin(x)*DEG_IN_RADIAN
    else:
        printerr("Error in min_max_alt -- arcsin(>1)\n")

    return (min,max)


######################################################################
def eclrot(mjd,x,y,z):
    """ rotates ecliptic rectangular coords x, y, z to
    equatorial (all assumed of date.)
    from skycalcv5
    """

    jd=mjd+2400000.5
    T=(mjd-J2000)/36525
    # 1992 Astron Almanac, p. B18, dropping the
    # cubic term, which is 2 milli-arcsec!
    incl = (23.439291 + T * (-0.0130042 - 0.00000016 * T))/DEG_IN_RADIAN
    ypr = math.cos(incl) * y - math.sin(incl) * z
    zpr = math.sin(incl) * y + math.cos(incl) * z
    # x remains the same
    return (x,ypr,zpr)

######################################################################
def geocent(geolong,geolat,height):
    """
    computes the geocentric coordinates from the geodetic
    (standard map-type) longitude, latitude, and height.
    These are assumed to be in decimal hours, decimal degrees, and
    meters respectively.  Notation generally follows 1992 Astr Almanac,
    p. K11

    from skycalcv5
    """

    geolat = geolat / DEG_IN_RADIAN
    geolong = geolong / HRS_IN_RADIAN
    denom = (1. - FLATTEN) * math.sin(geolat)
    denom = math.cos(geolat) * math.cos(geolat) + denom*denom
    C_geo = 1. / math.sqrt(denom)
    S_geo = (1. - FLATTEN) * (1. - FLATTEN) * C_geo
    # deviation from almanac notation -- include height here. 
    C_geo = C_geo + height / EQUAT_RAD
    S_geo = S_geo + height / EQUAT_RAD

    x_geo=C_geo * math.cos(geolat) * math.cos(geolong)
    y_geo=C_geo * math.cos(geolat) * math.sin(geolong)
    z_geo=S_geo * math.sin(geolat)

    return (x_geo,y_geo,z_geo)

######################################################################
# CALENDAR ROUTINES
######################################################################

######################################################################
def utc_gmst(ut):
    """ *  Conversion from universal time to sidereal time (double precision)
    given input time ut expressed as MJD
    result is GMST in hours
    """

    ut1=ut

    D2PI=6.283185307179586476925286766559
    S2R=7.272205216643039903848711535369e-5

    #  Julian centuries from fundamental epoch J2000 to this UT
    TU=(ut1-51544.5)/36525

    # GMST at this UT
    gmst=math.modf(ut1)[0]*D2PI+(24110.54841+(8640184.812866+(0.093104-6.2-6*TU)*TU)*TU)*S2R
    gmst=gmst*24/D2PI

    gmst=putrange(gmst)

    return gmst

###################################################################### 
def utc_lmst(ut,longitude):
    """ returns the LMST given the UT date/time (expressed as MJD),
    and longitude (degrees, + going to east)
    LMST is in hours
    """

    longitude=checksex(longitude)

    lmst=utc_gmst(ut)
    lmst+=longitude/15
    
    if (lmst<0):
        lmst+=24
    if (lmst>=24):
        lmst-=24
    return lmst

######################################################################
def mjd_to_epoch(mjd):
    """ convert date (in MJD) to epoch (fractional year)
    """
    
    epoch=2000+(mjd-J2000)/365.25
    return epoch
    
######################################################################
def etcorr(mjd):
    """ Given a julian date in 1900-2100, returns the correction
    delta t which is:
    TDT - UT (after 1983 and before 1998)
    ET - UT (before 1983)
    an extrapolated guess  (after 1998).
    
    For dates in the past (<= 1998 and after 1900) the value is linearly
    interpolated on 5-year intervals; for dates after the present,
    an extrapolation is used, because the true value of delta t
    cannot be predicted precisely.  Note that TDT is essentially the
    modern version of ephemeris time with a slightly cleaner
    definition.
    
    Where the algorithm shifts there is an approximately 0.1 second
    discontinuity.  Also, the 5-year linear interpolation scheme can
    lead to errors as large as 0.5 seconds in some cases, though
    usually rather smaller.

    from skycalcv5
    """

    jd=mjd+2400000.5
    jd1900=2415019.5
    dates=numarray.array(shape=[22],type='Float32')
    delts=numarray.array(shape=[21],type='Float32')

    for i in range(20):
        dates[i]=1900+i*5
    # the last accurate value
    dates[20]=1998

    delts[0] = -2.72
    delts[1] = 3.86
    delts[2] = 10.46
    delts[3] = 17.20
    delts[4] = 21.16
    delts[5] = 23.62
    delts[6] = 24.02
    delts[7] = 23.93
    delts[8] = 24.33
    delts[9] = 26.77
    delts[10] = 29.15
    delts[11] = 31.07
    delts[12] = 33.15
    delts[13] = 35.73
    delts[14] = 40.18
    delts[15] = 45.48
    delts[16] = 50.54
    delts[17] = 54.34
    delts[18] = 56.86
    delts[19] = 60.78
    delts[20] = 62.97

    year=1900+(jd-2415019.5)/365.25

    if (year<1998 and year >=1900):
        i=int((year-1900)/5)
        delt=delta[i]+((delta[i+1]-delta[i])/(dates[i+1]-dates[i]))*(year-dates[i])
    elif (year >=1998 and year < 2100):
        # rough extrapolation
        delt=33.15+(2.164e-3)*(jd-2436935.4)
    elif (year < 1900):
        printerr("No ephemeris data for < 1900\n")
        delt=0
    elif (year >=2100):
        printerr("Extrapolation in delta t too big\n")
        delt=180

    return delt

######################################################################
def cal_mjd(yr,mn,dy):
    """ convert calendar date to MJD
    year,month,day (may be decimal) are normal parts of date (Julian)"""
    
    m=mn
    if (yr<0):
        y=yr+1
    else:
        y=yr
    if (m<3):
        m+=12
        y-=1
    if (yr<1582 or (yr==1582 and (mn<10 or (mn==10 and dy<15)))):
        b=0
    else:
        a=int(y/100)
        b=int(2-a+a/4)
    
    jd=int(365.25*(y+4716))+int(30.6001*(m+1))+dy+b-1524.5
    mjd=jd-2400000.5

    return (mjd)

######################################################################
def mjd_cal(mjd):
    """convert MJD to calendar date (yr,mn,dy)
    """
    
    JD=mjd+2400000.5

    JD+=.5
    Z=int(JD)
    F=JD-Z
    if (Z<2299161):
        A=Z
    else:
        alpha=int((Z-1867216.25)/36524.25)
        A=Z+1+alpha-int(alpha/4)
    B=A+1524
    C=int((B-122.1)/365.25)
    D=int(365.25*C)
    E=int((B-D)/30.6001)
    day=B-D-int(30.6001*E)+F
    if (E<14):
        month=E-1
    else:
        month=E-13
    if (month<=2):
        year=C-4715
    else:
        year=C-4716

    return (year,month,day)


######################################################################
def find_dst_bounds(yr,stdtz,use_dst):
    """
    finds mjd's at which daylight savings time begins
    and ends.  The parameter use_dst allows for a number
    of conventions, namely:
    0 = don't use it at all (standard time all the time)
    1 = use USA convention (1st Sun in April to
    last Sun in Oct after 1986; last Sun in April before
    for 2007 & after, second Sun in March/first Sun in Nov )
    2 = use Spanish convention (for Canary Islands)
    -1 = use Chilean convention (CTIO).
    -2 = Australian convention (for AAT, MWA).
    Negative numbers denote sites in the southern hemisphere,
    where mjdb and mjde are beginning and end of STANDARD time for
    the year.
    It's assumed that the time changes at 2AM local time; so
    when clock is set ahead, time jumps suddenly from 2 to 3,
    and when time is set back, the hour from 1 to 2 AM local
    time is repeated.  This could be changed in code if need be."""
    

    if (use_dst==1 or use_dst==0):
        # USA
        # these versions are not current as of 2007
        if (yr >= 2007):
            logging.warning("Warning: DST calculation may be incorrect as of 2007...\n")
        if (yr<2007):
            mo=4
            if (yr>=1986):
                d=1
            else:
                d=30
        else:
            mo=3
            d=6
        h=2
        mn=0
        s=0
        #Find first Sunday in April for 1986 through 2006
        if (yr>=1986 & yr<2007):
            while (day_of_week(cal_mjd(yr,mo,d)) != 6):                
                d+=1
        elif (yr>=2007):
            # find second Sunday in March
            while (day_of_week(cal_mjd(yr,mo,d)) != 6):                
                d+=1
        else:
            # last Sunday in April for pre-1986
            while (day_of_week(cal_mjd(yr,mo,d)) != 6):
                d-=1
        mjdb=cal_mjd(yr,mo,d)+stdtz/24.0

        if (yr < 2007):
            # Find last Sunday in October        
            mo=10
            d=31
            while (day_of_week(cal_mjd(yr,mo,d)) != 6):
                d-=1
        else:
            # first sunday in November
            mo=11
            d=1
            while (day_of_week(cal_mjd(yr,mo,d)) != 6):
                d+=1
            
        mjde=cal_mjd(yr,mo,d)+(stdtz-1)/24.0

    elif (use_dst==2):
        # Spanish, for Canaries
        mo=3
        d=31
        h=2
        mn=0
        s=0
        while (day_of_week(cal_mjd(yr,mo,d)) != 6):
            d-=1
        mjdb=cal_mjd(yr,mo,d)+stdtz/24.0

        # Find last Sunday in October
        mo=9
        d=30
        while (day_of_week(cal_mjd(yr,mo,d)) != 6):
            d-=1
        mjde=cal_mjd(yr,mo,d)+(stdtz-1)/24.0
    elif (use_dst==-1):
        # Chilean
        # off daylight 2nd Sun in March, onto daylight 2nd Sun in October
        mo=3
        d=8
        h=2
        mn=0
        s=0
        while (day_of_week(cal_mjd(yr,mo,d)) != 6):
            d+=1
        mjdb=cal_mjd(yr,mo,d)+(stdtz-1)/24.0

        # mjdb last Sunday in October
        mo=10
        d=8
        while (day_of_week(cal_mjd(yr,mo,d)) != 6):
            d+=1
        mjde=cal_mjd(yr,mo,d)+(stdtz-0)/24.0
    elif (use_dst==-2):
        # Australian
        # off daylight 1st Sun in March, onto daylight last Sun in October
        mo=3
        d=1
        h=2
        while (day_of_week(cal_mjd(yr,mo,d)) != 6):
            d+=1
        mjdb=cal_mjd(yr,mo,d)+(stdtz-1)/24.0
        mo=10
        d=31
        while (day_of_week(cal_mjd(yr,mo,d)) != 6):
            d-=1
        mjde=cal_mjd(yr,mo,d)+(stdtz-1)/24.0      
 
    else:
        logging.warning("Unknown DST code: %d" % (use_dst))
        mjdb=0
        mjde=0

    return (mjdb,mjde)

######################################################################
def zonetime(use_dst,stdtz,mjd,mjdb,mjde):
    """Returns zone time offset when standard time zone is stdz,
           when daylight time begins (for the year) on jdb, and ends
           (for the year) on jde.  This is parochial to the northern
           hemisphere.  */
        /* Extension -- specifying a negative value of use_dst reverses
           the logic for the Southern hemisphere; then DST is assumed for
           the Southern hemisphere summer (which is the end and beginning
           of the year.) */
           """
    if (use_dst==0):
        return stdtz
    elif (mjd>mjdb and mjd<mjde and use_dst>0):
        return stdtz-1
    elif (mjd<mjdb or mjd>mjde and use_dst<0):
        return stdtz-1
    else:
        return stdtz


######################################################################
def day_of_week(mjd):
    """ returns day of week for mjd
    0=Mon
    6=Sun
    """

    jd=mjd+2400000.5

    jd+=0.5
    i=int(jd)
    x=i/7.0+0.01
    d=7*(x-int(x))
    return int(d)


######################################################################
# UTILITY FUNCTIONS
######################################################################

######################################################################
def adj_time(x):
    """ adjusts a time (decimal hours) to be between -12 and 12,
    generally used for hour angles.

    from skycalcv5"""
    if (math.fabs(x) < 100000.):        
        while(x > 12.):
            x = x - 24
        while(x < -12.):
            x = x + 24.
    else:
        printerr("Out of bounds in adj_time!\n")

    return(x)

######################################################################
def frac(x):
    """ return fractional part"""
    return (x-int(x))


######################################################################
def circulo(x):
    """ assuming x is an angle in degrees, returns
    modulo 360 degrees."""

    n=int(x/360)
    return (x-360*n)

######################################################################
def putrange(x,r=24):
    """ puts a value in the range [0,r)
    """

    if (not isinstance(x,numpy.ndarray)):
        while (x<0):
            x+=r
        while (x>=r):
            x-=r
        return x
    else:
        # numpy version
        while (numpy.any(x<0)):
            x[x<0]+=r
        while (numpy.any(x>=r)):
            x[x>=r]-=r
        return x
    
######################################################################
def interp1(X,Y,x):
    """1-D 2-point interpolation (linear)
    solves for y(x) given Y(X)
    """

    m=(Y[1]-Y[0])/(X[1]-X[0])
    y=m*(x-X[1])+Y[1]
    return y

######################################################################
def dec2sex(x):
    """ convert decimal to sexadecimal
    note that this fails for -1<x<0: d will be 0 when it should be -0
    """
    
    sign=1
    if (x<0):
        sign=-1
    x=math.fabs(x)

    d=int(x)
    m=int(60*(x-d))
    s=60*(60*(x-d)-m)
    if (sign == -1):
        d*=-1

    return (d,m,s)

######################################################################
def sex2dec(d,m,s):
    """ convert sexadecimal d,m,s to decimal
    d,m,s can be integer/float or string
    will only handle negative 0 correctly if it's a string
    """
    
    sign=1
    if (isinstance(d,int)):
        if (d<0):
            sign=-1
            d=math.fabs(d)
    elif isinstance(d,str):
        if (d.find('-') >= 0):
            sign=-1
        d=math.fabs(int(d))
    x=d+int(m)/60.0+float(s)/3600.0
    x=x*sign

    return x

######################################################################
def dec2sexstring(x, includesign=0,digits=2,roundseconds=0):    
    """
    dec2sexstring(x, includesign=0,digits=2,roundseconds=0)
    convert a decimal to a sexadecimal string
    if includesign=1, then always use a sign
    can specify number of digits on seconds (if digits>=0) or minutes (if < 0)
    """

    (d,m,s)=dec2sex(float(x))

    if (not roundseconds):
        sint=int(s)
        if (digits>0):
            sfrac=(10**digits)*(s-sint)
            ss2='%02' + 'd' + '.%0' + ('%d' % digits) + 'd'
            ss=ss2 % (sint,sfrac)
        elif (digits == 0):
            ss='%02d' % sint
        else:
            mfrac=10**(math.fabs(digits))*(s/60.0)
            ss2='%02' + 'd' + '.%0' + ('%d' % math.fabs(digits)) + 'd'
            ss=ss2 % (m,mfrac)
    else:
        sint=int(s)
        if (digits == 0):
            ss='%02d' % (round(s))
        elif (digits > 0):
            ss2='%02.' + ('%d' % digits) + 'f'            
            ss=ss2 % s
            if (s < 10):
                ss='0' + ss
        else:
            ss2='%02.' + ('%d' % math.fabs(digits)) + 'f'            
            ss=ss2 % (m+s/60.0)
            if (m < 10):
                ss='0' + ss
            
    
    if (not includesign):
        if (digits>=0):
            sout="%02d:%02d:%s" % (d,m,ss)
        else:
            sout="%02d:%s" % (d,ss)
        if (float(x)<0 and not sout.startswith("-")):
            sout='-' + sout
    else:
        sign='+'
        if (float(x)<0):
            sign='-'
        if (digits>=0):
            sout="%s%02d:%02d:%s" % (sign,math.fabs(d),m,ss)
        else:
            sout="%s%02d:%s" % (sign,math.fabs(d),ss)
        
    return sout

######################################################################
def sexstring2dec(sin):
    """ convert a sexadecimal string to a float
    string can be separated by colons or by hms, dms
    """

    d=0
    m=0
    s=0.0
    if (sin.find(':')>=0):
        # colon-separated values
        if (sin.count(':')==2):
            [d,m,s]=sin.split(':')
        elif (sin.count(':')==1):
            [d,m]=sin.split(':')
            s=0
    elif (sin.find('h')>=0):
        # hms separated
        j1=sin.find('h')
        j2=sin.find('m')
        j3=sin.find('s')
        if (j1>=0):
            d=sin[:j1]
            if (j2>j1):
                m=sin[j1+1:j2]
                if (j3>j2):
                    s=sin[j2+1:j3]
                elif (len(sin)>j2):
                    s=sin[j2+1:]
    elif (sin.find('d')>=0):
        # dms separated
        j1=sin.find('d')
        j2=sin.find('m')
        j3=sin.find('s')
        if (j1>=0):
            d=sin[:j1]
            if (j2>j1):
                m=sin[j1+1:j2]
                if (j3>j2):
                    s=sin[j2+1:j3]
                elif (len(sin)>j2):
                    s=sin[j2+1:]
  
    return sex2dec((d),(m),(s))

######################################################################
def checksex(x):
    """ check and see if the argument is a sexadecimal string
    or a float

    return the float version
    """
    
    y=0
    if (x != None):
        try:
            if ((x).count(':')>=1):
                y=sexstring2dec(x)
        except (TypeError,AttributeError):
            y=float(x)
        except:
            # print what the error was
            print "Unexpected error:", sys.exc_info()[0]
            y=0
    return y

######################################################################
def precomment(s):
    """ insert a comment (#) before every line of text
    """
    p=re.compile(r'^(\D)')
    p2=re.compile(r'\n(\D)')
    s2=p.sub(r'# \1',s)
    s3=p2.sub(r'\n# \1',s2)
    
    return s3

######################################################################
def printerr(s):
    """ writes s to stderr
    """

    logging.warning(s)

######################################################################
def moonplot(tm,Objs):

    # calculate moon at midnight
    Moon0=Moon(tm)
    LT0=tm.LT
    moonra=[]
    moondec=[]
    LTmin=-6
    LTmax=6
    dLT=6
    for LT in range(LTmin,LTmax+1,dLT):
        tm.LT=LT
        moon=Moon(tm)
        moonra.append(moon.obj.ra)
        moondec.append(moon.obj.dec)

    pgopen('%s/vcps' % 'test.ps')
    pgpap(0.0,1.0)    
    lwidth=2
    cheight=1.125
    lstyle=1
    fstyle=3
    pgslw(lwidth)
    pgsch(cheight)
    pgsls(lstyle)
    pgscf(fstyle)
    ypmin=0.15
    ypmax=0.85
    xpmin=0.15
    xpmax=0.85
    pgsvp(xpmin,xpmax,ypmin,ypmax)    

    if (tm.obs.lat>=0):
        ymin=-30
        ymax=90
    else:
        ymin=-90
        ymax=30
    pgenv(0,24,ymin,ymax,0,0)
    color0=pgqci()
    ls0=pgqls()

    ptsmoon=[23,15,2291]
    ptsmoon=[2291]
    pts=[0,2,3,4,5,7,11,12,13,14,16,17,18,-3,-4]

    docolor=1
    for i in range(len(Objs)):
        obj=Objs[i]
        ptuse=pts[(i % len(pts))]
        if (docolor):
            color=int(math.fmod(i,14)+color0)
        pgsci(color)
        pgpt(numarray.array([obj.ra]),numarray.array([obj.dec]),ptuse)
    pgsci(1)
    for i in range(len(moonra)):
        for j in range(len(ptsmoon)):
            pgpt(numarray.array([moonra[i]]),numarray.array([moondec[i]]),ptsmoon[j])
        

    pgclos()
######################################################################
def adtolb(RA,Dec):
    """
    [l,b]=adtolb2(RA,Dec)
    all in radians, (RA,Dec) are J2000
    this uses a direct tform from Allen's Astrophysical Quantities
    """

    a=RA
    d=Dec
    a0=282.86*numpy.pi/180;
    l0=(32.93)*numpy.pi/180;
    d0=(62.87)*numpy.pi/180;
    
    sinb=numpy.sin(d)*numpy.cos(d0)-numpy.cos(d)*numpy.sin(a-a0)*numpy.sin(d0);
    b=numpy.arcsin(sinb);
    cosb=numpy.cos(b);
    
    cosdl=numpy.cos(d)*numpy.cos(a-a0)/cosb;
    sindl=(numpy.sin(d0)*numpy.sin(d)+numpy.cos(d0)*numpy.cos(d)*numpy.sin(a-a0))/cosb;
    
    dl=numpy.arctan2(sindl,cosdl);
    l=dl+l0;  

    try:
        if (numpy.any(l>math.pi)):
            l[l>math.pi]-=2*math.pi
    except TypeError:
        if (l>math.pi):
            l-=2*math.pi
    return [l,b]

######################################################################
def lbtoad(l,b):
    """
    [a,d]=adtolb2(l,b)
    all in radians, (a,d) are J2000
    this may occasionally barf on the quadrants, since I only have the sin(RA) term
    taken from Allen's  
    """
    a0=282.86*math.pi/180
    l0=(32.93)*math.pi/180
    d0=(62.87)*math.pi/180

    if (isinstance(l,numpy.ndarray)):
        sind=numpy.cos(b)*numpy.sin(l-l0)*numpy.sin(d0)+numpy.sin(b)*numpy.cos(d0)
        d=numpy.arcsin(sind)
        cosd=numpy.cos(d)
        
        sinda=(numpy.cos(b)*numpy.sin(l-l0)*numpy.cos((d0))-numpy.sin(b)*numpy.sin((d0)))/cosd
        da=numpy.arcsin(sinda)
        a=da+a0
        
        a[numpy.where(cosd==0)]=0
        
        return [a,d]
    else:
        
        sind=math.cos(b)*math.sin(l-l0)*math.sin(d0)+math.sin(b)*math.cos(d0)
        d=math.asin(sind)
        cosd=math.cos(d)
        
        if (cosd == 0):
            a=0
        else:
            sinda=(math.cos(b)*math.sin(l-l0)*math.cos((d0))-math.sin(b)*math.sin((d0)))/cosd
            da=math.asin(sinda)
            a=da+a0
        return [a,d]
        
######################################################################
def galeq(l,b):
    """
    [RA,Dec]=galeq(l,b)
    Transformation from IAU 1958 galactic coordinates to
    J2000.0 equatorial coordinates (double precision)
    
    Given:
    DL,DB       dp       galactic longitude and latitude L2,B2
    
    Returned:
    DR,DD       dp       J2000.0 RA,Dec
    
    (all arguments are radians)
    
    Called:
    sla_DCS2C, sla_DIMXV, sla_DCC2S, sla_DRANRM, sla_DRANGE
    
    Note:
    The equatorial coordinates are J2000.0.  Use the routine
    sla_GE50 if conversion to B1950.0 'FK4' coordinates is
    required.
    
    Reference:
    Blaauw et al, Mon.Not.R.Astron.Soc.,121,123 (1960)
    
    P.T.Wallace   Starlink   21 September 1998
    
    Copyright (C) 1998 Rutherford Appleton Laboratory
    """


    """
    L2,B2 system of galactic coordinates
    
    P = 192.25       RA of galactic north pole (mean B1950.0)
    Q =  62.6        inclination of galactic to mean B1950.0 equator
    R =  33          longitude of ascending node
    
    P,Q,R are degrees
    
    Equatorial to galactic rotation matrix (J2000.0), obtained by
    applying the standard FK4 to FK5 transformation, for zero proper
    motion in FK5, to the columns of the B1950 equatorial to
    galactic rotation matrix:
    """

    if (isinstance(l,numpy.ndarray) and len(l)>1):
        R=numpy.zeros(l.shape)
        D=numpy.zeros(b.shape)
        for i in xrange(len(l)):
            [R[i],D[i]]=galeq(l[i],b[i])
        return [R,D]
    else:
        Rmat=numpy.array([[-0.054875539726,-0.873437108010,-0.483834985808],
                          [+0.494109453312,-0.444829589425,+0.746982251810],
                          [-0.867666135858,-0.198076386122,+0.455983795705]])
        # sperical to cartesian
        V1=dcs2c(l,b)
        
        # galactic to equatorial
        V2=dimxv(numpy.transpose(Rmat),V1)
        
        # cartesian to spherical
        [R,D]=dcc2s(V2)
        
        # put in range
        R=putrange(R,math.pi*2)
        
        return [R,D]

######################################################################
def dcs2c(A, B):
    """    
    *  Spherical coordinates to direction cosines (double precision)
    *
    *  Given:
    *     A,B       d      spherical coordinates in radians
    *                         (RA,Dec), (long,lat) etc.
    *
    *  Returned:
    *     V         d(3)   x,y,z unit vector
    *
    *  The spherical coordinates are longitude (+ve anticlockwise looking
    *  from the +ve latitude pole) and latitude.  The Cartesian coordinates
    *  are right handed, with the x axis at zero longitude and latitude, and
    *  the z axis at the +ve latitude pole.
    *
    *  Last revision:   26 December 2004
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    """

    if (isinstance(A,numpy.ndarray)):
        V=numpy.zeros((3,len(A)))
        COSB = numpy.cos(B)
        
        V[0,:] = numpy.cos(A)*COSB
        V[1,:] = numpy.sin(A)*COSB
        V[2,:] = numpy.sin(B)
        
        return V
    else:
        V=numpy.zeros((3,1))
        COSB = math.cos(B)
        
        V[0,:] = math.cos(A)*COSB
        V[1,:] = math.sin(A)*COSB
        V[2,:] = math.sin(B)
        return V
######################################################################
def dimxv(M, Va):
    """
    [Vb]=dimxv(M, Va)
    *  Performs the 3-D backward unitary transformation:
    *
    *     vector VB = (inverse of matrix M) * vector VA
    *
    *  (double precision)
    *
    *  (n.b.  the matrix must be unitary, as this routine assumes that
    *   the inverse and transpose are identical)
    *
    *  Given:
    *     DM       dp(3,3)    matrix
    *     VA       dp(3)      vector
    *
    *  Returned:
    *     VB       dp(3)      result vector
    *
    *  P.T.Wallace   Starlink   March 1986
    *
    *  Copyright (C) 1995 Rutherford Appleton Laboratory
    """

    Vb=numpy.array(numpy.mat(M)*numpy.mat(Va))
    return Vb

######################################################################    
def dcc2s(V):
    """
    *  Cartesian to spherical coordinates (double precision)
    *
    *  Given:
    *     V     d(3)   x,y,z vector
    *
    *  Returned:
    *     A,B   d      spherical coordinates in radians
    *
    *  The spherical coordinates are longitude (+ve anticlockwise looking
    *  from the +ve latitude pole) and latitude.  The Cartesian coordinates
    *  are right handed, with the x axis at zero longitude and latitude, and
    *  the z axis at the +ve latitude pole.
    *
    *  If V is null, zero A and B are returned.  At either pole, zero A is
    *  returned.
    *
    *  Last revision:   22 July 2004
    *
    *  Copyright P.T.Wallace.  All rights reserved.
    """

    if (len(V.shape)==1 or V.shape[1]==1):
        x=V[0]
        y=V[1]
        z=V[2]
        R=math.sqrt(x*x+y*y)
        if (R == 0):
            A=0
        else:
            A=math.atan2(y,x)
        if (z == 0):
            B=0
        else:
            B=math.atan2(z,R)
        return [A,B]
    

######################################################################
def calcGPSseconds_noleap(MJD,UT):
    """
    calculate the GPSseconds corresponding to the date MJD (days) and time UT (hours)
    ignores leap seconds
    """
    return round(((MJD+UT/24.0)-GPSseconds_MJDzero)*86400)

######################################################################
def calcUTGPSseconds_noleap(GPSseconds):
    """
    calculate the MJD (days) and UT (hours) corresponding to the time in GPSseconds
    ignores leap seconds
    """

    MJD=int((GPSseconds)/86400.0)+GPSseconds_MJDzero
    UT=(((GPSseconds/86400.0)-int((GPSseconds)/86400.0))*24)
    return [MJD,UT]

######################################################################
def calcUTGPSseconds(GPSseconds):
    """
    calculate the MJD (days) and UT (hours) corresponding to the time in GPSseconds
    includes leap seconds from EHM
    """

    i0=3

    try:
        offset_seconds=(numpy.array(Offset_seconds)[(GPSseconds>numpy.array(GPSseconds_Start))*(GPSseconds<=numpy.array(GPSseconds_End))])[0]
    except IndexError:
        logging.warning("Leap second table not valid for GPSseconds=%d.  Returning value without leap seconds." % GPSseconds)
        return calcUTGPSseconds_noleap(GPSseconds)
    offset_seconds-=Offset_seconds[i0]

    y=GPSseconds+offset_seconds-GPSseconds_Start[i0]-1
    x=y/86400.0
    MJD=math.floor(x)+MJD_Start[i0]
    UT=((y-86400*math.floor(x)))/3600.0
    return [MJD,UT]

######################################################################
def calcGPSseconds(MJD, UT=0):
    """
    calculate the GPSseconds corresponding to the date MJD (days) and time UT (hours)
    based on leap seconds provided by EHM
    """

    try:
        offset_seconds=(numpy.array(Offset_seconds)[(MJD>numpy.array(MJD_Start))*(MJD<=numpy.array(MJD_End))])[0]
    except IndexError:
        logging.warning("Leap second table not valid for MJD=%d.  Returning value without leap seconds." % MJD)
        return calcGPSseconds_noleap(MJD,UT)
    return (MJD-40587)*86400+UT*3600-offset_seconds
######################################################################
def GPSseconds_now():
    """
    calculate the GPSseconds corresponding to the current time
    """

    x=time.gmtime()
    MJD=cal_mjd(x[0],x[1],x[2])
    UT=x[3]+x[4]/60.0+x[5]/3600.0
    return calcGPSseconds(MJD,UT)

######################################################################
def GPSseconds_now_f():
    """
    CW: calculates the current GPSseconds including fractional seconds
    """

    x=datetime.datetime.utcnow()
    MJD=cal_mjd(x.year,x.month,x.day)
    UT=x.hour+x.minute/60.0+(x.second+x.microsecond/1000000.0)/3600.0
    return calcGPSseconds(MJD,UT)


######################################################################
def GPSseconds_next(GPSseconds=None, buffer=1):
    """
    gpsseconds=GPSseconds_next(GPSseconds=None, buffer=1)
    return the next 8-s boundary in GPSseconds
    if argument is None, will use GPSseconds_now(), otherwise will calculate the next time based on the argument
    if buffer > 0, then the time returned will be >= buffer seconds from argument
    """
    
    if (GPSseconds):
        x=GPSseconds
    else:
        x=GPSseconds_now()
    if (buffer):
        x+=buffer
    return (int(x+9)&int("fffffff8",16))

######################################################################
def rdtoxy(fitshd, RA, Dec):
    """
    [x,y]=rdtoxy(fitshd,ra,dec)
    convert (ra,dec) (degrees) to (x,y) (pixels)
    using the FITS header in fitshd
    """

    try:
        CD1_1=fitshd['CD1_1']
        CD2_2=fitshd['CD2_2']
        try:
            CD2_1=fitshd['CD2_1']
            CD1_2=fitshd['CD1_2']
        except:
            CD2_1=0
            CD1_2=0

    except:
        CD1_1=fitshd['CDELT1']
        CD2_2=fitshd['CDELT2']
        CD1_2=0
        CD2_1=0

    det=(CD1_1*CD2_2-CD1_2*CD2_1)

    CDINV1_1=CD2_2/det
    CDINV1_2=-CD1_2/det
    CDINV2_1=-CD2_1/det
    CDINV2_2=CD1_1/det

    ra0=fitshd['CRVAL1'] * math.pi/180
    dec0=fitshd['CRVAL2']*math.pi/180

    ra=RA*math.pi/180
    dec=Dec*math.pi/180
    if (isinstance(ra,numpy.ndarray)):        
        bottom=numpy.sin(dec)*numpy.sin(dec0)+numpy.cos(dec)*numpy.cos(dec0)*numpy.cos(ra-ra0)
        
        xi=numpy.cos(dec)*numpy.sin(ra-ra0)/bottom
        eta=(numpy.sin(dec)*numpy.cos(dec0)-numpy.cos(dec)*numpy.sin(dec0)*numpy.cos(ra-ra0))/bottom
    else:
        bottom=math.sin(dec)*math.sin(dec0)+math.cos(dec)*math.cos(dec0)*math.cos(ra-ra0)
        
        xi=math.cos(dec)*math.sin(ra-ra0)/bottom
        eta=(math.sin(dec)*math.cos(dec0)-math.cos(dec)*math.sin(dec0)*math.cos(ra-ra0))/bottom
        

    xi*=180/math.pi
    eta*=180/math.pi

    x=CDINV1_1*xi+CDINV1_2*eta+fitshd['CRPIX1']
    y=CDINV2_1*xi+CDINV2_2*eta+fitshd['CRPIX2']

    return (x,y)

######################################################################
# OBSERVATORY DEFINITIONS
######################################################################

######################################################################
def print_obs(itoprint=-1):
    """ print all of the observatories
    """
    if (itoprint >= 0):
        print Obs[itoprint]
    else:
        for i in range(0,len(Obs)):
            print "%s\n" % Obs[i]

# entries have: Code, Name, long. (deg), lat. (deg), elev. (m), TZ (hr), DST, TZ code
Obs=[]
Obs.append(Observatory('LCO','Las Campanas','-70:42:00','-29:00:30',2282,4,-1,"C"))
Obs.append(Observatory('KPNO','Kitt Peak',-7.44111*15,31.9533,700,7,0,"M"))
Obs.append(Observatory('LS','ESO La Silla',-4.7153*15,-29.257,2347,4,-1,"C"))
Obs.append(Observatory('CP','ESO Cerro Paranal',-4.69356*15,-24.625,2635,4,-1,"C"))
Obs.append(Observatory('MP','Mount Palomar',-7.79089*15,33.35667,1706,8,1,"P"))
Obs.append(Observatory('CTIO','Cerro Tololo',-4.721*15,-30.165,2215,4,-1,"C"))
Obs.append(Observatory('MK','Mauna Kea',-10.36478*15,19.8267,4215,10,0,"H"))
Obs.append(Observatory('MH','Mount Hopkins (MMT)',-7.39233*15,31.6883,2608,7,0,'M'))
Obs.append(Observatory('LO','Lick',-8.10911*15,37.3433,1290,8,1,'P'))
#Obs.append(Observatory('LP','La Palma',-1.192*15,28.75833,0,2,'G'))
Obs.append(Observatory('MWA','Murchison Widefield Array (32T)','116:40:14.93','-26:42:11.95',377.8,-8,-2,"W"))
obscode={}
for i in range(len(Obs)):
    obscode[Obs[i].code]=i



######################################################################
def usage():

    (xdir,xname)=os.path.split(sys.argv[0])
    print "Usage:  %s [-h] [-r <ra> -d <dec> [-n <name>]] -D <date> -o <observatory> [-i <input_file>] [-p 0/1] [-f 0/1] [-c 0/1] [-t <text>]" % xname



######################################################################

if __name__=="__main__":
    main.doplot=doplot
    main()


