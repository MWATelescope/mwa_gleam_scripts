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
      'hours_scheduled': round(self.hours_scheduled or 0., 4),
      'hours_observed': round(self.hours_observed or 0., 4),
      'hours_with_data': round(self.hours_with_data or 0., 4),
      'hours_with_uvfits': round(self.hours_with_uvfits or 0., 4),
      'data_transfer_rate': round(self.data_transfer_rate or 0., 4),
    }
