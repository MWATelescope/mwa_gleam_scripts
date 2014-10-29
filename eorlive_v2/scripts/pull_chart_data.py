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

TESTING = False

cur_d = os.path.dirname(__file__)

def write_to_log(msg):
  print msg
  if TESTING: return
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
    WHERE subq.files > 0
    ORDER BY subq.starttime ASC''')

  write_to_log("mwa_setting_rows query ran in %f seconds" %profile())

  ngas_files_rows = send_ngas_query(
  '''
  SELECT DISTINCT file_id FROM ngas_files
  ORDER BY file_id ASC
  '''
  )

  write_to_log("ngas_files_rows query ran in %f seconds" %profile())

  write_to_log("preparing for the giant interation where mwa_setting_rows = %d and ngas_files_rows = %d"
    % (mwa_setting_rows.rowcount, ngas_files_rows.rowcount ))
  i = 0
  total_data_hours = 0
  no_more_ngas_files = False
  match = 0
  no_match = 0
  weirdness = 0
  not_weird = 0
  for row in mwa_setting_rows:
    #if i >= 10: break
    obsid = int(row[0])
    obsid_str=str(obsid)
    num_ngas_files = 0

    while(True):
      ngas_file = ngas_files_rows.fetchone()
      if not ngas_file:
        no_more_ngas_files = True
        break;

      ngas_file_id = ngas_file[0]

      try:
        ngas_file_obsid = int(ngas_file_id.split("_")[0])
      except ValueError as e:
        #print "VALUE ERROR ngas_file_id = %s" %ngas_file_id
        ngas_file_obsid = 0 # so it can be just fast forwarded

      #print "%s starts with %s ?" %(ngas_file_id, obsid_str)

      if ngas_file_id.startswith(obsid_str):
        num_ngas_files += 1
        match += 1
        #print "match"
      else:

        # fast forward if ngas_file_obsid is smaller - for any normal situation it should be equal or greater
        if ngas_file_obsid < obsid:
          #print "ngas_file_obsid < obsid"
          continue

        # if not move the cursor one step back and break so it fetches the same row on the next loop
        ngas_files_rows.scroll(-1)
        no_match += 1
        #print "no match"
        break;

    num_mit_files = row[2]
    #print "obsid = %d num_ngas_files = %d" % (obsid, num_ngas_files)
    if num_ngas_files > num_mit_files:
      print "what the hell! More files in ngas! obsid = %d num_mit_files = %s num_ngas_files = %d" % (obsid, num_mit_files, num_ngas_files)
      weirdness += 1
    else:
      not_weird += 1
    total_data_hours += (float(num_ngas_files) / float(num_mit_files)) * (row[1] - row[0]) / 3600.
    i += 1

    if no_more_ngas_files: break;

  print "match = %d no_match = %d" %(match, no_match)
  print "weirdness = %d not_weird = %d" %(weirdness, not_weird)

  write_to_log("The giant iteration ran in %f seconds" %profile())

  # UVFITS hours
  total_uvfits_hours = float (send_mwa_query(
    '''
    SELECT COUNT(*) FROM uvfits_location WHERE version = 4 AND subversion = 1
    ''').fetchone()[0] ) * 112. / 3600.

  write_to_log("total_uvvits_hours query ran in %f seconds" %profile())

  # Data transfer rate
  data_transfer_rate = send_ngas_query(
  """
  select sum(uncompressed_file_size)/date_part('epoch', to_timestamp('%(now)s','YYYY-MM-DD"T"HH24:MI:SS.MS')- to_timestamp(min(ingestion_date),'YYYY-MM-DD"T"HH24:MI:SS.MS') )/(1024^2) as "data_transfer_rate"
from ngas_files
where ingestion_date between to_char(to_timestamp('%(now)s','YYYY-MM-DD"T"HH24:MI:SS.MS')- interval '24 hours','YYYY-MM-DD"T"HH24:MI:SS.MS') and '%(now)s';
  """ % {"now": datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000')}
  ).fetchone()[0] or 0
  data_transfer_rate = float(data_transfer_rate)

  write_to_log("data_transfer_rate query ran in %f seconds" %profile())

  write_to_log("\nTotal Scheduled Hours = %.6f" %total_sch_hours)
  write_to_log("Total Observed Hours = %.6f" %total_obs_hours)
  write_to_log("Total Hours that have data = %.6f" %total_data_hours)
  write_to_log("Total Hours that have uvfits data = %.6f" %total_uvfits_hours)
  write_to_log("Data transfer rate = %.6f" %data_transfer_rate)

  if TESTING: return exit(0)

  send_local_query("""
    INSERT INTO graph_data (hours_scheduled, hours_observed, hours_with_data, hours_with_uvfits, data_transfer_rate)
    VALUES (%f, %f, %f, %f, %f)
  """ %(total_sch_hours, total_obs_hours, total_data_hours, total_uvfits_hours, data_transfer_rate))

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
