#!/usr/bin/env python

import subprocess as sp
import psycopg2, os, glob
from datetime import datetime

PATH_TO_LOG = '/tmp/current_beam.log'
PATH_TO_PNGS = '/var/beam_images/'

env = os.getenv('EOR_ENV', "dev")

if env == "prod":
  GET_OBS_INFO = '/home/ubuntu/MWA_Tools/scripts/get_observation_info.py'
elif env =="stage":
  GET_OBS_INFO = '/home/ubuntu/MWA_Tools/scripts/get_observation_info.py'
else:
  GET_OBS_INFO = '/mnt/MWA_Tools/scripts/get_observation_info.py'


cur_d = os.path.dirname(__file__)

MAX_FILES = 100 # number of files to keep in the beam image directory

def write_to_log(msg):
  print msg
  f=open(os.path.join(cur_d, PATH_TO_LOG),'a')
  try:
    f.write(msg)
  finally:
    f.close()

def trim_files():
  images = []
  for f in os.listdir(PATH_TO_PNGS):
    if f.endswith(".png"):
      images.append(f)

  images = sorted(images, reverse=True)
  deleted_files = 0

  for i in range(0, len(images)):
    if i < MAX_FILES: continue
    fname = (images[i])
    write_to_log("%r file deleted \n" %fname)
    os.remove(os.path.join(PATH_TO_PNGS, fname))
    deleted_files += 1

  write_to_log("%d files deleted because of the set file limit - %d \n" %(deleted_files, MAX_FILES))

if __name__=="__main__":
  write_to_log("\n-- %s -- \n" %datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f%z"))
  #get the last command in mwa_setting
  eorconn = psycopg2.connect(database='mwa',host='eor-db.mit.edu',user='mwa',password='BowTie')
  cur = eorconn.cursor()
  cur.execute('''
    select starttime from mwa_setting
    where starttime < gpsnow()
    and (projectid = 'G0009' or projectid = 'G0010')
    order by starttime desc limit 1
    ''')
  obsid=cur.fetchall()[0][0]
  eorconn.close()

  exitcode = sp.call('cd %s && %s -g %s -i' %(PATH_TO_PNGS, GET_OBS_INFO, str(obsid)), shell=True)
  write_to_log("get_observation_info ran with obsid = %d | exit code = %d \n" %(obsid, exitcode))
  trim_files()
