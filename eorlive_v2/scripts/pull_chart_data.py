#!/usr/bin/env python

import psycopg2, os, glob
from datetime import datetime
from mwapy.ephem_utils import GPSseconds_now

PATH_TO_LOG = '/tmp/pull_chart_data.log'
LOCAL_DB_HOST = 'localhost'
LOCAL_DB_U = 'postgres'
LOCAL_DB_P = 'postgres'
eor_conn = None # Lazy load globals
ngas_conn = None
mwa_conn = None
local_conn = None
profiling_mark = None

cur_d = os.path.dirname(__file__)

def write_to_log(msg):
  print msg
  f=open(os.path.join(cur_d, PATH_TO_LOG),'a')
  try:
    f.write(msg)
  finally:
    f.close()

def send_query(db, query):
  cur = db.cursor()
  cur.execute(query)
  return cur

def send_eor_query(query): return send_query(eor_conn, query)

def send_ngas_query(query): return send_query(ngas_conn, query)

def send_mwa_query(query): return send_query(mwa_conn, query)

def send_local_query(query): return send_query(local_conn, query)

def profile():
  global profiling_mark
  result = datetime.now() - profiling_mark
  profiling_mark = datetime.now()
  return result.total_seconds()

def calculate_total_hours(rows):
  totobssecs=0.
  for row in rows:
      totobssecs = totobssecs + row[1] - row[0]
  return totobssecs / 3600.

def update():
  gps_now=GPSseconds_now()
  profiling_mark = datetime.now()

  # Total Scheduled
  total_sch_hours = float ( send_eor_query('''
    SELECT SUM(stoptime-starttime) FROM mwa_setting
    WHERE projectid=\'G0009\'
  ''').fetchone()[0] ) / 3600.

  write_to_log("total_sch_hours query ran in %f seconds" %profile())

  # Total Observed
  total_obs_hours = float (send_eor_query('''
    SELECT SUM(stoptime-starttime) FROM mwa_setting
    WHERE projectid=\'G0009\' AND stoptime < %d
  ''' %gps_now).fetchone()[0] ) / 3600.

  write_to_log("total_obs_hours query ran in %f seconds" %profile())

  # Total that has data
  mwa_setting_rows =  send_eor_query('''
    SELECT subq.starttime, subq.stoptime, subq.files
    FROM
      (SELECT starttime, stoptime, COUNT(data_files.id) as files
      FROM mwa_setting
      LEFT OUTER JOIN data_files ON mwa_setting.starttime = data_files.observation_num
      WHERE projectid='G0009'
      GROUP BY starttime, stoptime) as subq
    WHERE subq.files > 0''').fetchall()

  write_to_log("mwa_setting_rows-that-have-more-than-one-file query ran in %f seconds" %profile())

  write_to_log("preparing for the dreadful n queries where n = %d" %len(mwa_setting_rows) )
  i = 0
  total_data_hours = 0
  for row in mwa_setting_rows:
    #if i >= 10: break
    obsid=str(int(row[0]))
    num_ngas_files = send_ngas_query('''
      SELECT COUNT(DISTINCT file_id) FROM ngas_files WHERE file_id LIKE '%s%%'
    ''' %obsid).fetchone()[0]
    num_mit_files = row[2]
    total_data_hours += (float(num_ngas_files) / float(num_mit_files)) * (row[1] - row[0]) / 3600.
    i += 1

  write_to_log("dreadful n queries ran in %f seconds" %profile())

  # total_data_hours = float (send_eor_query('''
  #   SELECT SUM(subq.stoptime-subq.starttime)
  #   FROM
  #     (SELECT starttime, stoptime, COUNT(data_files.id) as files
  #     FROM mwa_setting
  #     LEFT OUTER JOIN data_files ON mwa_setting.starttime = data_files.observation_num
  #     WHERE projectid='G0009'
  #     GROUP BY starttime, stoptime) as subq
  #   WHERE subq.files > 0
  # ''').fetchone()[0] ) / 3600.

  # UVFITS hours
  total_uvfits_hours = float (send_mwa_query(
    '''
    SELECT COUNT(*) FROM uvfits_location WHERE version = 3 AND subversion = 1
    ''').fetchone()[0] ) * 112. / 3600.

  write_to_log("total_uvvits_hours query ran in %f seconds" %profile())

  # TODO Data transfer rate

  write_to_log("\nTotal Scheduled Hours = %.6f" %total_sch_hours)
  write_to_log("Total Observed Hours = %.6f" %total_obs_hours)
  write_to_log("Total Hours that have data = %.6f" %total_data_hours)
  write_to_log("Total Hours that have uvfits data = %.6f" %total_uvfits_hours)

  # TODO insert data_transfer_rate
  send_local_query("""
    INSERT INTO graph_data (hours_scheduled, hours_observed, hours_with_data, hours_with_uvfits)
    VALUES (%f, %f, %f, %f)
  """ %(total_sch_hours, total_obs_hours, total_data_hours, total_uvfits_hours))

  local_conn.commit()

if __name__=='__main__':

  write_to_log("\n-- %s -- \n" %datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f%z"))

  # Establish the database connection
  try:
    eor_conn = psycopg2.connect(database='mwa',host='eor-db.mit.edu',user='mwa',password='BowTie')
  except Exception, e:
    write_to_log("Can't connect to the eor database at eor-db.mit.edu - %s" %e)
    exit(1)

  try:
    ngas_conn = psycopg2.connect(database='ngas',user='ngas_ro',host='ngas.mit.edu',password='ngas$ro')
  except Exception, e:
    write_to_log("Can't connect to the ngas database at ngas.mit.edu - %s" %e)
    exit(1)

  try:
    mwa_conn = psycopg2.connect(database='mwa',user='mwa',password='BowTie',host='mwa.mit.edu')
  except Exception, e:
    write_to_log("Can't connect to the mwa database at mwa.mit.edu - %s" %e)
    exit(1)

  try:
    local_conn = psycopg2.connect(database='eor',user=LOCAL_DB_U,password=LOCAL_DB_P,host=LOCAL_DB_HOST)
  except Exception, e:
    write_to_log("Can't connect to the local database at %s - %s" %(LOCAL_DB_HOST,e))
    exit(1)

  profiling_mark = datetime.now()

  try:
    update()
  finally:
    eor_conn.close()
    ngas_conn.close()
    mwa_conn.close()
    local_conn.close()
