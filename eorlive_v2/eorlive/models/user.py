from eorlive import db
import hashlib
from datetime import datetime

class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(128))
  username = db.Column(db.String(128), unique=True)
  email = db.Column(db.String(128))
  password = db.Column(db.String(64))
  created_at = db.Column(db.DateTime)

  def __init__(self, name, username, password, email):
    self.name = name
    self.username = username
    self.password = hashlib.sha256(password).hexdigest()
    self.email = email
    self.created_at = datetime.now()

  def asDict(self):
    return {
      'id': self.id,
      'name': self.name,
      'email': self.email,
      'username': self.username,
      'created_at': self.created_at
    }

  def is_authenticated(self):
    return True

  def is_active(self):
    return True

  def is_anonymous(self):
    return False

  def get_id(self):
    return unicode(self.id)

  def __repr__(self):
    return '<User %r>' % (self.username)
