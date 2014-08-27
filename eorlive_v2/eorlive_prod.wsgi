activate_this = '/opt/pyvenv/eorlive/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

import sys
sys.path.insert(0,'/home/ubuntu/MWA_Tools/eorlive_v2')

from eorlive import app as application
