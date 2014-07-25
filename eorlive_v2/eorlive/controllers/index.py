from eorlive import app
from flask import render_template, request
from flask.ext.login import login_required, current_user

@app.route('/')
def index():
  return render_template('index.html')

@app.route('/login')
def index_login():
  return render_template('login.html')

@app.route('/old_data')
@login_required
def index_old_data():
  return render_template('old_data.html')
