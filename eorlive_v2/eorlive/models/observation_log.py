from eorlive import db
from datetime import datetime
import math

class ObservationLog(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  created_date = db.Column(db.DateTime)
  observed_date = db.Column(db.DateTime)
  author_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
  note = db.Column(db.Text)
  tags = db.Column(db.Integer, nullable=False, default=0)
  deleted_date = db.Column(db.DateTime)

  def __init__(self, observed_date, author_user_id, note, tags):
    self.observed_date = observed_date
    self.author_user_id = author_user_id
    self.note = note
    self.tags = tags

  def asDict(self):
    return {
      'id': self.id,
      'created_date': self.created_date,
      'observed_date': self.observed_date,
      'author_user_id': self.author_user_id,
      'note':self.note,
      'tags': self.tags
    }

  # tag values
  BAD = math.pow(2,0)
  FINE = math.pow(2,1)
  NO_DATA = math.pow(2,2)
  HW_FAULT = math.pow(2,3)
  DATAFLOW_FAULT = math.pow(2,4)
  CORRELATOR_FAULT = math.pow(2,5)
  OPS_ISSUE = math.pow(2,6)
