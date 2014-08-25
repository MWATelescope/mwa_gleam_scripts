from eorlive import app
from flask import jsonify, request
from eorlive import db, mit_db_engine, cache
from flask.ext.login import login_required, current_user

@app.route('/api/mit_data/observations', methods=['GET'])
@cache.cached(timeout=600) # Cached for 10 minutes
def get_current_and_past_observations():

  LIMIT = 5

  query ="""
    SELECT observation_number, obsname, projectid, timestamp_gps(starttime) as start_time, timestamp_gps(stoptime) as stop_time, COUNT(data_files.id) as files
    FROM obsc_mwa_setting
    LEFT OUTER JOIN data_files ON obsc_mwa_setting.observation_number = data_files.observation_num
    WHERE projectid='G0009' or projectid='G0010' AND starttime < gpsnow()
    GROUP BY observation_number, obsname, projectid, starttime, stoptime
    ORDER BY starttime DESC
    LIMIT %d
  """ %(LIMIT)

  conn = mit_db_engine.connect()

  try:
    result = conn.execute(query)
  finally:
    conn.close()

  observations = []

  for row in result:
    observations.append({
      "observation_number": row["observation_number"],
      "obsname": row["obsname"],
      "projectid": row["projectid"],
      "start_time": row["start_time"],
      "stop_time": row["stop_time"],
      "files": row["files"]
    })

  return jsonify({"observations": observations})

@app.route('/api/mit_data/future_observation_counts', methods=['GET'])
@cache.cached(timeout=600) # Cached for 10 minutes
def get_future_observation_counts():
  query = """
    SELECT count(*)
    FROM mwa_setting
    WHERE starttime>gpsnow() %s AND (projectid='G0009' or projectid='G0010')
  """

  conn = mit_db_engine.connect()

  try:
    result_total = conn.execute(query %"")
    result_next_24 = conn.execute(query %"AND stoptime<(gpsnow()+86400)")
  finally:
    conn.close()

  return jsonify({
    "total": result_total.first()[0],
    "next_24": result_next_24.first()[0]
  })
