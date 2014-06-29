from flask import Flask
app = Flask('eorlive')
app.debug = True
#app.config.from_pyfile('settings.py')
from eorlive.controllers import *
