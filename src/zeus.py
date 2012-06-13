#!/usr/bin/python

import os
import sys
cmdname = os.path.basename(sys.argv[0])
if not cmdname:
  cmdname = 'zeus.py'

USAGE = """
Usage:

%s plugs
  Show the ID string, connected device name, and current power switch
  status for plugs 1-20

%s info
  Show the local temperature, as well as current, voltage and power
  for branches A and B

%s on <plug> <plug> <plug> ...
  Turn ON each of the plugs specified on the command line.
  Plug specifiers can be an integer from 1-20, or a branch letter and integer
  Plugs 1-10 are A1-A10, while plugs 11-20 are B1-B10 (for example, you can
  use 3 or A3, 15 or B5, etc)

%s off <plug> <plug> <plug> ...
  Turn OFF each of the specified plugs.

%s updatedb
  Update the postgres database tables with the current values of the
  temperature and power values - not yet implemented.
""" % (cmdname,cmdname,cmdname,cmdname,cmdname)


"""Module documentation:

   Library to communicate with the Western Telematic Managed Power Controller via SNMP.

   Also doubles as a command line utility to read status data and toggle switch status.

""" + USAGE

import snmp

zeus = snmp.SNMP(user='ZeusSuper', password='SuperZeus', host='zeus')

ON = snmp.rfc1902.Integer(5)
OFF = snmp.rfc1902.Integer(6)

ROOT = (1,3,6,1,4,1,2634,3)

PLUGNUMBERS = {}
PLUGNAMES = {}
PLUGSTATUSES = {}
PLUGIDS = {}


def TempInC():
  """Return the temperature of the MPC, in degrees C
  """
  return int(zeus.getCmd(ROOT+(200,10,1,3,1))[0][1])

def CurrentA():
  """Return the current in Amps for branch A (plugs A1-A10)
  """
  return float(zeus.getCmd(ROOT+(200,10,1,4,1))[0][1])/10.0

def VoltageA():
  """Return the voltage for branch A (plugs A1-A10)
  """
  return int(zeus.getCmd(ROOT+(200,10,1,5,1))[0][1])

def PowerA():
  """Return the power in Watts for branch A (plugs A1-A10)
  """
  return int(zeus.getCmd(ROOT+(200,10,1,6,1))[0][1])

def CurrentB():
  """Return the current in Amps for branch B (plugs B1-B10)
  """
  return float(zeus.getCmd(ROOT+(200,10,1,7,1))[0][1])/10.0

def VoltageB():
  """Return the voltage for branch B (plugs B1-B10)
  """
  return int(zeus.getCmd(ROOT+(200,10,1,8,1))[0][1])

def PowerB():
  """Return the power in Watts for branch B (plugs B1-B10)
  """
  return int(zeus.getCmd(ROOT+(200,10,1,9,1))[0][1])

def plugname(plugnumber):
  """Return the configurable full name of the the device attached to the given plug.

     Arguments:
       plugnumber - an integer from 1-20 (1-10 are plugs A1-A10, 11-20 are B1-B10)

     Returns:
       string containing full name of device attached to that plug.
  """
  return str(zeus.getCmd(ROOT+(100,200,1,5,plugnumber))[0][1])

def plugid(plugnumber):
  """Return the ID string of the the device attached to the given plug.

     Arguments:
       plugnumber - an integer from 1-20 (1-10 are plugs A1-A10, 11-20 are B1-B10)

     Returns:
       string containing the ID for that plug - eg 'LOCAL - A5'
  """
  return str(zeus.getCmd(ROOT+(100,200,1,2,plugnumber))[0][1])

def plugstatus(plugnumber):
  """Return the power switch status (on or off) of the given plug.

     Arguments:
       plugnumber - an integer from 1-20 (1-10 are plugs A1-A10, 11-20 are B1-B10)

     Returns:
       0 if the plug is switched off, 1 if the plug is switched on
  """
  return int(zeus.getCmd(ROOT+(100,200,1,3,plugnumber))[0][1])

def plugon(plugnumber):
  """Turn the power ON to the plug specified by 'plugnumber'.

     Arguments:
       plugnumber - an integer from 1-20 (1-10 are plugs A1-A10, 11-20 are B1-B10)

     Returns:
       None
  """
  varBinds = zeus.setCmd((ROOT+(100,200,1,4,plugnumber),ON))

def plugoff(plugnumber):
  """Turn the power OFF to the plug specified by 'plugnumber'.

     Arguments:
       plugnumber - an integer from 1-20 (1-10 are plugs A1-A10, 11-20 are B1-B10)

     Returns:
       None
  """
  varBinds = zeus.setCmd((ROOT+(100,200,1,4,plugnumber),OFF))


def GetPlugData():
  """Connect to the MPC and download the plug ID strings, device names and power 
     switch state for each of the 20 plugs on the MPC. 

     Stores the data in global dictionaries PLUGIDS, PLUGNAMES and PLUGSTATUSES (indexed
     by plug number (an integer from 1-20), as well as the reverse mapping in global
     dictionary PLUGNUMBERS (indexed by device name)

     No args, returns None
  """
  idlist = zeus.bulkCmd(0,20,ROOT+(100,200,1,2,0))
  namelist = zeus.bulkCmd(0,20,ROOT+(100,200,1,5,0))
  statuslist = zeus.bulkCmd(0,20,ROOT+(100,200,1,3,0))
  for p in range(1,21):
    pid = str(idlist[p-1][0][1])
    name = str(namelist[p-1][0][1])
    status = int(statuslist[p-1][0][1])
    PLUGIDS[p] = pid
    PLUGNAMES[p] = name
    PLUGSTATUSES[p] = status
    PLUGNUMBERS[name] = p


if __name__ == '__main__':
  if len(sys.argv) == 1 or sys.argv[1].upper() == '-H':
    print USAGE
  else:
    action = sys.argv[1].upper()
    if action == 'PLUGS':
      GetPlugData()
      states = {0:'OFF', 1:'ON'}
      for p in range(1,21):
        print "Plug %2d is %3s - [%s]: %s" % (p, states[PLUGSTATUSES[p]], PLUGIDS[p], PLUGNAMES[p])
    elif action == 'INFO':
      print "Temp is %d degrees C." % (TempInC())
      print "Branch A is using %3.1f Amps (%4d Watts) at %d Volts." % (CurrentA(), PowerA(), VoltageA())
      print "Branch B is using %3.1f Amps (%4d Watts) at %d Volts." % (CurrentB(), PowerB(), VoltageB())
    elif (action == 'ON') or (action == 'OFF'):
      GetPlugData()
      for arg in sys.argv[2:]:
        try:
          p = int(arg)
        except ValueError:
          if arg[0].upper() == 'A' or arg[0].upper() == 'B':
            try:
              p = int(arg[1:])
              if arg[0].upper() == 'B':
                p = p + 10
            except ValueError:
              print "Invalid plug number:",arg
              break
          else:
            print "Invalid plug number:",arg
            break
        if (p >= 1) and (p <= 20):
          if action == 'ON':
            plugon(p)
            print "Plug number %d [%s] connected to '%s' turned %s" % (p,PLUGIDS[p],PLUGNAMES[p],action)
          else:
            res = raw_input("Are you sure you want to turn off '%s'? (y/n):" % PLUGNAMES[p])
            if res and (res.upper()[0] == 'Y'):
              plugoff(p)
              print "Plug number %d [%s] connected to '%s' turned %s" % (p,PLUGIDS[p],PLUGNAMES[p],action)
            else:
              print "Action cancelled for plug: %s" % arg
    elif action == 'updatedb':
      print "Not yet implemented."


