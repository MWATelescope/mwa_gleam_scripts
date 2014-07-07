from eorlive import app
from flask import jsonify, request
from sqlalchemy.exc import IntegrityError
from eorlive.libs.helper import validate_req_params
from eorlive.models.admin_user import AdminUser
from eorlive import db

@app.route('/api/admin_users', methods=['POST'])
def create_admin_user():
    pass

@app.route('/api/admin_users/<int:id>', methods=['GET'])
def show_admin_user(id):
  return jsonify({
    'foo':'bar'
  })
