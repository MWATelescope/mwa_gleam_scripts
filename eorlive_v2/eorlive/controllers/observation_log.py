import os
from eorlive import app
from flask import jsonify, request
from eorlive import db, mit_db_engine, cache
from flask.ext.login import login_required, current_user
from eorlive.models.observation_log import ObservationLog
from eorlive.models.user import User
from sqlalchemy import desc
from datetime import datetime

@app.route('/api/observation_logs', methods=['GET', 'POST'])
@login_required
def observation_log_get_post():
  if request.method == 'POST':
    note = request.form.get('note', '')
    observed_date_str = request.form.get('observed_date')
    try:
      observed_date = datetime.strptime(observed_date_str, "%Y-%m-%d")
    except ValueError, e:
      return "could not parse observed_date", 400
    author_user_id = current_user.id
    tags = int(request.form.get('tags') or 0)
    observation_log = ObservationLog(observed_date, author_user_id, note, tags)
    db.session.add(observation_log)
    db.session.commit()
    return jsonify(observation_log.asDict()), 201
  else:
    tags = int(request.args.get('tags') or 0)
    limit = int(request.args.get('limit') or 10)
    offset = int(request.args.get('offset') or 0)
    logs = []
    for log, user in db.session.query(ObservationLog, User
      ).filter(ObservationLog.author_user_id == User.id
      ).filter(ObservationLog.tags.op('&')(tags) == tags
      ).order_by(desc(ObservationLog.observed_date)
      ).offset(offset).limit(limit):
      log_dict = log.asDict()
      log_dict["author_user_name"] = user.name
      logs.append(log_dict)
    return jsonify({
      "observation_logs" : logs
    })


@app.route('/api/observation_logs/<int:id>', methods=['PUT', 'DELETE'])
@login_required
def observation_log_put_delete():
  observation_log = ObservationLog.query.filter_by(id=id).first()

  if not observation_log:
    return "no such observation_log", 404

  if observation_log.author_user_id != current_user.id:
    return "you are not authorized to modify or delete this observation log", 403

  if request.method == 'DELETE':
    db.session.delete(observation_log)
    db.session.commit()
    return "{}", 200
  else:
    observation_log.note = request.form.get('note', observation_log.note)
    if request.form.has_key('observed_date'):
      observed_date_str = request.form.get('observed_date')
      try:
        observed_date = datetime.strptime(observed_date_str, "%Y/%m/%d")
      except ValueError, e:
        return "could not parse observed_date", 400
      observation_log.observed_date = observed_date
    observation_log.tags = int(request.form.get('tags', observation_log.tags))
    db.session.commit()
    return jsonify(observation_log.asDict()), 201
