from eorlive import app
from flask import render_template, request

@app.route('/')
def index():
  return render_template('index.html')

@app.route('/login')
def index_login():
  return render_template('login.html')
