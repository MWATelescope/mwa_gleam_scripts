import os
from eorlive import app
from flask import jsonify, request
from eorlive import db, mit_db_engine, cache
from flask.ext.login import login_required, current_user
from eorlive.models.graph_data import GraphData
from sqlalchemy import desc
from datetime import datetime, timedelta

@app.route('/api/graph_data', methods=['GET'])
def graph_data():

  last_x_months = int(request.args.get("last_x_months", 0))

  query = GraphData.query

  if last_x_months > 0:
    last_x_months_ago = datetime.now() - timedelta(days=30.42*last_x_months)
    query = query.filter(GraphData.created_date >= last_x_months_ago)

  graph_data = [gd.asDict() for gd in query.order_by(GraphData.created_date).all()]
  return jsonify({
    "graph_data": graph_data
  })
