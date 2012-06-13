#!/bin/env python
from  mwapy import dbobj

class data_file(dbobj.dbObject):
    _table='data_files'
    _attribs=[('observation_num','observation_num',0),
               ('filetype','filetype',0),
               ('site_path','site_path',''),
               ('filename','filename',''),
               ('host','host',''),
               ('size','size',0)]
    _readonly=[]
    _key=('filename','observation_num')
    _nmap={}
    _reprf='%(name)s'
    _srtf='MWA data file[%(name)s]'
    for oname,dname,dval in _attribs:
        _nmap[oname] = dname

               



