from eorlive import db
import hashlib
from datetime import datetime

class GraphData(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  created_date = db.Column(db.DateTime)
  hours_scheduled = db.Column(db.Float)
  hours_observed = db.Column(db.Float)
  hours_with_data = db.Column(db.Float)
  hours_with_uvfits = db.Column(db.Float)
  data_transfer_rate = db.Column(db.Float)

  def __init__(self):
    pass

  def asDict(self):
    return {
      'id': self.id,
      'created_date': self.created_date,
      'hours_scheduled': self.hours_scheduled,
      'hours_observed': self.hours_observed,
      'hours_with_data': self.hours_with_data,
      'hours_with_uvfits': self.hours_with_uvfits,
      'data_transfer_rate': self.data_transfer_rate,
    }
