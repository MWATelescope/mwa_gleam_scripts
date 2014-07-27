import os
from eorlive import app
from flask import jsonify, request
from eorlive import db, mit_db_engine, cache
from flask.ext.login import login_required, current_user
from eorlive.models.graph_data import GraphData
from sqlalchemy import desc

@app.route('/api/graph_data', methods=['GET'])
@login_required
def graph_data():
  graph_data = [gd.asDict() for gd in GraphData.query.order_by(GraphData.created_date).all()]
  return jsonify({
    "graph_data": graph_data
  })
