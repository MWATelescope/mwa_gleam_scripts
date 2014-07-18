#!/usr/bin/env python

import subprocess as sp
import psycopg2, os, glob
from datetime import datetime

PATH_TO_GET_OBSERVATION_INFO = '../../scripts/get_observation_info.py'
PATH_TO_LOG = '/tmp/current_beam.log'
PATH_TO_PNGS = '/var/beam_images/'

cur_d = os.path.dirname(__file__)

def write_to_log(msg):
  print msg
  f=open(os.path.join(cur_d, PATH_TO_LOG),'a')
  try:
    f.write(msg)
  finally:
    f.close()

if __name__=="__main__":
    #get the last command in mwa_setting
    eorconn = psycopg2.connect(database='mwa',host='eor-db.mit.edu',user='mwa',password='BowTie')
    cur = eorconn.cursor()
    cur.execute('select starttime from mwa_setting where starttime < gpsnow() order by starttime desc limit 1')
    obsid=cur.fetchall()[0][0]

    #get current observation and store it in the defined directory
    png_fname = os.path.join(cur_d, PATH_TO_PNGS, "%s.png" %str(obsid))
    print "generating the png file at %s" %png_fname
    sp.call('%s -f %s -g -%s -i' %(os.path.join(cur_d, PATH_TO_GET_OBSERVATION_INFO), png_fname, str(obsid)), shell=True)

    # copy the generated file to current_beam.png
    cbeam_fname = os.path.join(cur_d, PATH_TO_PNGS, "current_beam.png")
    print "trying to copy the generated file to %s" %cbeam_fname
    try:
      sp.call("cp -rf %s %s" % (png_fname, cbeam_fname) )
      write_to_log('%s successfully executed' %datetime.now().isoformat(' '))
    except OSError, e:
      write_to_log('%s failed to generate image' %datetime.now().isoformat(' '))
    exit(0)
