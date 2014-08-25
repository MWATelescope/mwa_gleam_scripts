import os
from eorlive import app
from flask import jsonify, request
from eorlive import db, mit_db_engine, cache
from flask.ext.login import login_required, current_user

PNG_FILE_PATH = "/var/beam_images"

@app.route('/api/beam_images', methods=['GET'])
def get_beam_images():
  """
  Return files in the beam_images directories in an ordered manner.
  param limit: how many files it should return
  param offset: from what offset
  """
  images = []
  limit = int(request.args.get('limit') or 10)
  offset = int(request.args.get('offset') or 0)

  curr = 0

  for f in sorted(os.listdir(PNG_FILE_PATH), reverse=True):
    if f.endswith(".png"):
      if curr < offset:
        curr += 1
        continue
      images.append(f)
      curr += 1
      if curr >= (offset+limit): break

  return jsonify({
    "images": sorted(images, reverse=True)
  })
