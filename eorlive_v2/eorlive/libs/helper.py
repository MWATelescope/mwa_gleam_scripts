def validate_req_params(params, keys):
  for k in keys:
    if not params.has_key(k): return False
  return True
