import os
from taskinit import *

import numpy
import math
import mwapb


def pbgain(imagename=None,pbimage=None,overwrite=True,isodipole=False,dbdelay=False,dbhost=None,dbuser=None,dbpass=None,delays=None):


    if dbdelay is True:
        raise ValueError("dbdelay=True is not implemented yet!")

    if dbdelay is False and delays is None:
        raise ValueError("No delays specified!")


    delays=numpy.array(delays)
    if delays.size != 16:
        raise ValueError("There must be 16 delay elements given: %s, %s"%(`delays.size`,`delays`))


    print "Delays: ",delays
    #get the image date
    ia.open(imagename)
    coordsys=ia.coordsys()
    epoch=coordsys.epoch()
    time=me.getvalue(epoch).values()[0]
    print "Map date: ",qa.time(time,form='dmy')
    s=ia.shape()
    nx=s[0]
    ny=s[1]
    #ns=s[2]
    #nf=s[3]
    ns=1
    nf=1


    print "Calculating az/el of map pixels"

    xy=numpy.mgrid[0:nx,0:ny,0:1,0:1]
    xyr=numpy.double(xy.reshape(4,nx*ny))
    out=coordsys.convertmany(coordin=xyr,absin=[True,True,True,True],unitsin=['pix','pix','pix','pix'],absout=[True,True,True,True],unitsout=['rad','rad','pix','pix'])
    #out=coordsys.toabsmany(xyr,isworld=1)



    meas=ia.coordmeasures()
    dd=meas['measure']['direction']
    dd['m0']['value']=out[0,:]
    dd['m0']['unit']='rad'
    dd['m1']['value']=out[1,:]
    dd['m1']['unit']='rad'

    me.doframe(me.observatory('Askap'))
    me.doframe(epoch)
    azel=me.measure(dd,'azel')
    az=(azel['m0']['value']*180.0/math.pi).reshape(nx,ny)
    el=(azel['m1']['value']*180.0/math.pi).reshape(nx,ny)

    ia.close()

    allstokes=coordsys.stokes()
    specax=coordsys.findcoordinate(type='Spectral')['world']
    stokesax=coordsys.findcoordinate(type='Stokes')['world']

    print "Az/El at map center:"+`az[nx/2,ny/2]`+','+`el[nx/2,ny/2]`


    print "Generating pb pattern"
    out=numpy.zeros(shape=s,dtype='float64')


    tbeam=mwapb.MWA_tile_gain()
    if isodipole:
        tbeam.vpat.set_element_patterns(mwapb.isotropic_dipole_vpat())

    tbeam.set_delays(delays)

    for fr in range(s[specax]):
        tpix=numpy.array(s)*0
        tpix[specax]=fr
        freq=coordsys.toworld(tpix)['numeric'][specax]
        tbeam.set_freq(freq)
        if s[stokesax] == 1:
           st = 0
           stokes=allstokes
           tbeam.set_stokes(stokes)
           g=tbeam.calculate(az,el)
           if specax==2 and stokesax==3:
               out[:,:,fr,st]=g
           elif specax==3 and stokesax==2:
               out[:,:,st,fr]=g
        else:
           for st in range(s[stokesax]):
               stokes=allstokes[st]
               tbeam.set_stokes(stokes)
               g=tbeam.calculate(az,el)
               if specax==2 and stokesax==3:
                  out[:,:,fr,st]=g
               elif specax==3 and stokesax==2:
                  out[:,:,st,fr]=g

    ia.fromarray(outfile=pbimage,pixels=out,csys=coordsys.torecord(),overwrite=overwrite)
    ia.close()
