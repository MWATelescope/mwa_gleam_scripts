from flask import Flask
import os, calendar
from datetime import datetime, timedelta

app = Flask('eorlive')
app.permanent_session_lifetime = timedelta(hours=24)

env = os.getenv('EOR_ENV', "dev")

if env == "prod":
  # Prod Settings
  app.config.from_pyfile('settings_prod.py')
elif env =="stage":
  # Stage Settings
  app.config.from_pyfile('settings_stage.py')
else:
  # Default: Dev Settings
  app.config.from_pyfile('settings_dev.py')

from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.login import LoginManager
from flask.ext.cache import Cache
from flask.json import JSONEncoder

db = SQLAlchemy(app)
migrate = Migrate(app, db)
mit_db_engine = db.get_engine(app, bind="mit")

manager = Manager(app)
manager.add_command('db', MigrateCommand)

from user_command import UserCommand
manager.add_command('user', UserCommand)

login_manager = LoginManager()
login_manager.init_app(app)

cache = Cache(app,config={'CACHE_TYPE': 'simple'})

# Customize jsonify

class CustomJSONEncoder(JSONEncoder):
  def default(self, obj):
    try:
      if isinstance(obj, datetime):
        if obj.utcoffset() is not None:
          obj = obj - obj.utcoffset()
        millis = int(
          calendar.timegm(obj.timetuple()) * 1000 +
          obj.microsecond / 1000
        )
        return millis
      iterable = iter(obj)
    except TypeError:
      pass
    else:
      return list(iterable)
    return JSONEncoder.default(self, obj)

app.json_encoder = CustomJSONEncoder

# Load Controllers
from eorlive.controllers import *
