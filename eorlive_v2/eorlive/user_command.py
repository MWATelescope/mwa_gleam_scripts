from flask.ext.script import Command, Manager, Option
import hashlib
from sqlalchemy.exc import IntegrityError
from eorlive.models.user import User
from eorlive import db
from datetime import datetime

UserCommand = Manager(usage = 'Perform admin user creation and update')

@UserCommand.option('-n', '--name', dest = 'name', default = None, help = "Full name of the user")
@UserCommand.option('-e', '--email', dest = 'email', default = None, help = "Email address of the user")
@UserCommand.option('-u', '--username', dest = 'username', default = None, help = "Username for the user. Used for logging in.")
@UserCommand.option('-p', '--password', dest = 'password', default = None, help = "Password for the user. Used for logging in.")
def create_admin(name, email, username, password):
  if not name or not email or not username or not password:
    print "Please pass all required parameters.\n Usage: python -m eorlive user create_admin -n <name> -e <email> -u <username> -p <password>"
  else:
    user = User(name, username, password, email)
    user.admin_level = 1
    db.session.add(user)

    try:
      db.session.commit()
      print "Admin user created"
    except IntegrityError, e:
      print "Could not create admin user. Duplicate username."

@UserCommand.option('-u', '--username', dest = 'username', default = None, help = "Username for the user.")
@UserCommand.option('-p', '--password', dest = 'password', default = None, help = "New password.")
def reset_password(username, password):
  if not username or not password:
    print "Please pass all required parameters.\n Usage: python -m eorlive user reset_password -u <username> -p <password>"
  else:
    user = User.query.filter_by(username=username).first()
    if not user:
      print "No such user found"
      return
    user.password = hashlib.sha256(password).hexdigest()
    db.session.add(user)

    try:
      db.session.commit()
      print "User password updated"
    except Exception as e:
      print "Something had gone wrong. ", e

@UserCommand.option('-u', '--username', dest = 'username', default = None, help = "Username for the user.")
@UserCommand.option('-a', '--admin_level', dest = 'admin_level', default = None, help = "New admin level value in integer. 0 means no admin authority.")
def set_admin_level(username, admin_level):
  if not username or not admin_level:
    print "Please pass all required parameters.\n Usage: python -m eorlive user set_admin_level -u <username> -a <admin_level>"
  else:
    user = User.query.filter_by(username=username).first()
    if not user:
      print "No such user found"
      return
    try:
      user.admin_level = int(admin_level)
    except ValueError as e:
      print "Please use an integer value for -a/--admin_level"
      return
    db.session.add(user)

    try:
      db.session.commit()
      print "User admin level updated"
    except Exception as e:
      print "Something had gone wrong. ", e
