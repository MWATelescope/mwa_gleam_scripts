import hashlib
from eorlive import app
from flask import jsonify, request
from sqlalchemy.exc import IntegrityError
from eorlive.libs.helper import validate_req_params
from eorlive.models.user import User
from eorlive import db
from eorlive import login_manager
from flask.ext.login import login_required, login_user, logout_user, current_user

# For now use POST /api/users with name,username,password,email,key to create new users

@app.route('/api/users', methods=['POST'])
def create_user():

  # FOR NOW, LET'S USE A SECRET KEY FOR CREATING USERS
  if request.form.get("key")!="21CM":
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

@app.route('/api/users/<int:id>', methods=['GET'])
def show_user(id):
  user = User.query.filter_by(id=id).first()
  if not user:
    return "no such user", 404
  return jsonify(user.asDict()), 200

@app.route('/api/current_user', methods=['GET'])
@login_required
def show_current_user():
  return jsonify(current_user.asDict()), 200

@app.route('/api/login', methods=['POST'])
def user_login():
  username = request.form['username']
  password = request.form['password']
  user = User.query.filter_by(username=username,password=hashlib.sha256(password).hexdigest()).first()
  if not user:
    return "Wrong username or password", 403
  login_user(user)
  return "login success", 201

@app.route('/api/logout', methods=['GET', 'POST'])
def user_logout():
  logout_user()
  return "logout success"

@login_manager.user_loader
def load_user(userid):
    return User.query.filter_by(id=userid).one()
