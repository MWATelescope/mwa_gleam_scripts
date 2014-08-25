import hashlib
from eorlive import app
from flask import jsonify, request
from sqlalchemy.exc import IntegrityError
from eorlive.libs.helper import validate_req_params
from eorlive.models.user import User
from eorlive import db
from eorlive import login_manager
from flask.ext.login import login_required, login_user, logout_user, current_user
from datetime import datetime

# For now use POST /api/users with name,username,password,email,key to create new users

@app.route('/api/users/<int:id>', methods=['GET'])
def show_user(id):
  user = User.query.filter_by(id=id).first()
  if not user:
    return "no such user", 404
  return jsonify(user.asDict()), 200

@app.route('/api/current_user', methods=['GET','PUT'])
@login_required
def show_current_user():
  if request.method == 'PUT':
    return update_current_user()
  return jsonify(current_user.asDict()), 200

def update_current_user():
  password = request.form.get('password')
  name = request.form.get("name")
  email = request.form.get("email")

  if password:
    current_user.password = hashlib.sha256(password).hexdigest()
  if name:
    current_user.name = name
  if email:
    current_user.email = email

  db.session.add(current_user)
  db.session.commit()

  return jsonify(current_user.asDict()), 200

@app.route('/api/login', methods=['POST'])
def user_login():
  username = request.form['username']
  password = request.form['password']
  user = User.query.filter_by(username=username,password=hashlib.sha256(password).hexdigest()).first()
  if not user:
    return "Wrong username or password", 400
  login_user(user)
  return jsonify(current_user.asDict()), 201

@app.route('/api/logout', methods=['GET', 'POST'])
def user_logout():
  logout_user()
  return "logout success"

@login_manager.user_loader
def load_user(userid):
    return User.query.filter_by(id=userid).first()

# ADMIN STUFF

@app.route('/api/users', methods=['POST'])
@login_required
def create_user():

  if current_user.admin_level < 1:
    return jsonify({"error": "you are not authorized"}), 403

  if not validate_req_params(request.form, ["name", "username", "password", "email"]):
    return jsonify({"error": "required parameters not passed"}), 400

  user = User(request.form["name"], request.form["username"], request.form["password"], request.form["email"])
  db.session.add(user)

  try:
    db.session.commit()
  except IntegrityError, e:
    return jsonify({"error": "username already exists."})

  return jsonify(user.asDict()), 201

@app.route('/api/users/admin', methods=['POST'])
def create_admin_user():

  # Secret
  if request.form.get("key")!="GiantEarthing":
    return jsonify({"error": "you are not authorized"}), 403

  if not validate_req_params(request.form, ["name", "username", "password", "email"]):
    return jsonify({"error": "required parameters not passed"}), 400

  user = User(request.form["name"], request.form["username"], request.form["password"], request.form["email"])
  user.admin_level = 1
  db.session.add(user)

  try:
    db.session.commit()
  except IntegrityError, e:
    return jsonify({"error": "username already exists."})

  return jsonify(user.asDict()), 201

@app.route('/api/users', methods=['GET'])
@login_required
def show_users():

  if current_user.admin_level < 1:
    return jsonify({"error": "you are not authorized"}), 403

  return jsonify({
    'users': [u.asDict() for u in User.query.order_by(User.id).all()]
  }), 200

@app.route('/api/users/<int:id>', methods=['PUT'])
@login_required
def edit_user(id):

  if current_user.admin_level < 1:
    return jsonify({"error": "you are not authorized"}), 403

  user = User.query.filter_by(id=id).first()
  if not user:
    return "no such user", 404

  if user.admin_level > 0:
    return jsonify({"error": "you are not authorized"}), 403

  if request.form.get("reactivate") == "true":
    user.deactivated_date = None
  elif request.form.get("deactivate") == "true":
    user.deactivated_date = datetime.now()

  user.name = request.form.get("name", user.name)
  user.email = request.form.get("email", user.email)
  if request.form.has_key("password"):
    user.password = hashlib.sha256(request.form.get("password")).hexdigest()
  user.admin_level = request.form.get("admin_level", user.admin_level)

  db.session.add(user)
  db.session.commit()

  return jsonify(user.asDict())
