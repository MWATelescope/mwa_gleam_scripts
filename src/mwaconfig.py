"""Put this file into a system-wide python path so it will always be 
   available.

   This module handles configuration for the MWA python code. It creates
   a ConfigParser object, reads in config files from two possible
   locations (/usr/local/etc and .), then creates a basic class for
   each section and loads the items in that section. All items read
   are returned as strings, no matter what the contents.
   
   If the M&C Python source tree (underneath MandC/ in
   git) is in the current Python Path (eg the PYTHON_PATH
   environment variable has been set correctly) then that path is
   used for future imports. However, if a test import fails, the
   default python path is read (a comma seperated list of pathnames
   in the 'pypath' field in the 'glob' section of the config file),
   and each path it contains is added to sys.path.
   
   This means that only this file (mwaconfig.py) needs
   to be in the system-wide site-packages directory for all MWA
   M&C code to work, provided an:
   
   import mwaconfig
   
   is run before any other M&C import lines.
   
   
   Accessing config data can be done without any knowledge of
   ConfigParser internals, eg:
   
   from mwaconfig import mandc
   db = schedule.getdb(user = mandc.dbuser, 
                       password = mandc.dbpass,
                       host = mandc.dbhost,
                       database = mandc.dbname)
                       
   This is the easiest method to access the config file data, but will
   throw an exception if the parameter named (eg 'dbuser') is not in
   the 'mandc' section of the config file, or if the section named, eg
   '[mandc]' isn't in the config file at all.
   
   For python path variables, a helper function 'addpath' is included to
   parse a comma seperated list of paths in one string, and append each of 
   them in turn to sys.path, if it doesn't already contain that path.
   
   Alternatively, you can use the ConfigParser instance directly, eg:
   
   import mwaconfig
   if mwaconfig.CP.has_option('mandc','dbuser'):
     dbuser = mwaconfig.CP.get('mandc','dbuser')
     
   Section and option names are case insensitive, but used in the
   code in lower case for consistency. 
   
   The contents of the config file should consist of section names in
   [square brackets]    on a line by themselves, with each section
   name followed by one or more 'name: value' pairs. Values may refer
   to other options within that section (or an optional 'DEFAULT'
   section) using standard Python string formatting  "%(name)s"
   format. Comments can be included in the config file on lines starting
   with '#' or ';'. For example:

   -----------------------
   [DEFAULT]
   pypath: /home/mwa/MandC
   # This puts this pypath value in every section, unless overridden
   
   [glob]
   numtiles: 32
   
   [mandc]
   baselog: /var/log
   statuslog: %(baselog)s/Status
   errorlog: %(baselog)s/errors
   
   [rts]
   pypath: /tmp/test/MandC   /home/randall/rtspipe
   -----------------------
   
   The above file would give:
   
   mwaconfig.glob.numtiles = '32'
   mwaconfig.glob.pypath = '/home/mwa/MandC'

   mwaconfig.mandc.pypath = '/home/mwa/MandC'
   mwaconfig.mandc.baselog = '/var/log'
   mwaconfig.mandc.statuslog = '/var/log/Status'
   mwaconfig.mandc.errorlog = '/var/log/errors'

   mwaconfig.rts.pypath = '/tmp/test/MandC, /home/randall/rtspipe'
   
"""   

#Path to read config data from. The contents of all files listed
#here are merged, with the file/s list LAST taking precedence
#over the contents of any files listed earlier. If one or more
#of the files listed below is missing it's simply skipped,
#with no error.
#
#This allows any user to copy the global config file to the 
#current directory and edit whatever fields they want, or to
#create a local config file in the current directory with
#only a few fields in it, and all other data will be taken
#from the global config file.

#Both 'mwa.conf' and 'mwa-local.conf' are read (with 'local' 
#taking precedence) so that 'mwa.conf' can be reserved for
#configuration data that's the same on all machines, with
#automatic propagation, and 'mwa-local.conf' can be used
#to override data that's different on a specific machine.


CPpath = ['/usr/local/etc/mwa.conf', '/usr/local/etc/mwa-local.conf',
          './mwa.conf', './mwa-local.conf']

import sys
import ConfigParser

CP = ConfigParser.SafeConfigParser(defaults={})
CPfile = CP.read(CPpath)
if not CPfile:
  print "None of the specified configuration files found by mwaconfig.py: %s" % (CPpath,)
  
class _AttClass:
  pass
  
for _s in CP.sections():
  globals()[_s] = _AttClass()
  for _name,_value in CP.items(_s):
    setattr(globals()[_s],_name,_value)


def addpath(newpaths):
  """For each one of the comma-seperated path strings in the string 'newpaths',
     append the given path string to the current value of sys.path,
     provided sys.path doesn't already contain it.
  """
  for s in newpaths.split(','):
    if s.strip() not in sys.path:
      sys.path.append(s.strip())

# Try importing the 'config_local.py' module. If it succeeds, a valid PYTHON_PATH
# has been set (eg ~/MandC). If there is an ImportError exception, 
# read the default path from the [glob] section of the config file, and 
# add it to sys.path.

try:
  from mwapy import config_local     #Any other MWA-wide config can be put here.
except ImportError:
  if ('glob' in globals()) and (hasattr(glob,'pypath')):
    addpath(glob.pypath)  
    from mwapy import config_local
  else:
    print "module mwaconfig: Can't find valid MWA python path."

  

  
