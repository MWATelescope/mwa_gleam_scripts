from flask import Flask
import os

app = Flask('eorlive')

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

db = SQLAlchemy(app)
migrate = Migrate(app, db)
mit_db_engine = db.get_engine(app, bind="mit")

manager = Manager(app)
manager.add_command('db', MigrateCommand)

login_manager = LoginManager()
login_manager.init_app(app)

cache = Cache(app,config={'CACHE_TYPE': 'simple'})

# Load Controllers
from eorlive.controllers import *
