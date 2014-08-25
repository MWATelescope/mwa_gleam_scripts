import os
import pytz
from eorlive import app
from flask import jsonify, request
from eorlive import db, mit_db_engine, cache
from flask.ext.login import login_required, current_user
from eorlive.models.observation_log import ObservationLog
from eorlive.models.user import User
from sqlalchemy import desc
from datetime import datetime

@app.route('/api/observation_logs', methods=['GET', 'POST'])
def observation_logs_get():

  tags = int(request.args.get('tags') or 0)
  limit = int(request.args.get('limit') or 10)
  offset = int(request.args.get('offset') or 0)
  from_date = request.args.get('from_date')
  to_date = request.args.get('to_date')
  logs = []

  query = db.session.query(ObservationLog, User
    ).filter(ObservationLog.author_user_id == User.id
    ).filter(ObservationLog.deleted_date == None)

  if tags > 0:
    query = query.filter(ObservationLog.tags.op('&')(tags) > 0)

  if from_date:
    try:
      from_date = datetime.strptime(from_date, "%Y-%m-%d")
    except ValueError, e:
      return "could not parse from_date", 400
    query = query.filter(ObservationLog.observed_date >= from_date)

  if to_date:
    try:
      to_date = datetime.strptime(to_date, "%Y-%m-%d")
    except ValueError, e:
      return "could not parse to_date", 400
    query = query.filter(ObservationLog.observed_date <= to_date)

  for log, user in query.order_by(desc(ObservationLog.observed_date)
    ).offset(offset).limit(limit):
    log_dict = log.asDict()
    log_dict["author_user_name"] = user.name
    logs.append(log_dict)
  return jsonify({
    "observation_logs" : logs
  })

@app.route('/api/observation_logs/new', methods=['POST'])
@login_required
def observation_log_post():
  note = request.form.get('note', '')
  observed_date_str = request.form.get('observed_date')
  try:
    observed_date = datetime.strptime(observed_date_str, "%Y-%m-%d")
    observed_date = pytz.utc.localize(observed_date)
  except ValueError, e:
    return "could not parse observed_date", 400
  author_user_id = current_user.id
  tags = int(request.form.get('tags') or 0)
  observation_log = ObservationLog(observed_date, author_user_id, note, tags)
  observation_log.created_date = datetime.now()
  db.session.add(observation_log)
  db.session.commit()
  return jsonify(observation_log.asDict()), 201

@app.route('/api/observation_logs/<int:id>', methods=['PUT', 'DELETE'])
@login_required
def observation_log_put_delete(id):
  observation_log = ObservationLog.query.filter_by(id=id).first()

  if not observation_log:
    return "no such observation_log", 404

  if observation_log.author_user_id != current_user.id and not current_user.admin_level:
    return "you are not authorized to modify or delete this observation log", 403

  if request.method == 'DELETE':
    observation_log.deleted_date = datetime.now()
    db.session.add(observation_log)
    db.session.commit()
    return "{}", 200
  else:
    observation_log.note = request.form.get('note', observation_log.note)
    if request.form.has_key('observed_date'):
      observed_date_str = request.form.get('observed_date')
      try:
        observed_date = datetime.strptime(observed_date_str, "%Y-%m-%d")
        observed_date = pytz.utc.localize(observed_date)
      except ValueError, e:
        return "could not parse observed_date", 400
      observation_log.observed_date = observed_date
    observation_log.tags = int(request.form.get('tags', observation_log.tags))
    db.session.commit()
    return jsonify(observation_log.asDict()), 201

@app.route('/api/observation_logs/latest', methods=['GET'])
def latest_observation_log():

  log, user = db.session.query(ObservationLog, User
    ).filter(ObservationLog.author_user_id == User.id
    ).filter(ObservationLog.deleted_date == None
    ).order_by(desc(ObservationLog.observed_date)).first()

  log_dict = log.asDict()
  log_dict["author_user_name"] = user.name

  return jsonify(log_dict)
