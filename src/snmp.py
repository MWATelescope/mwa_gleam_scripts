#!/usr/bin/python


"""Module documentation:

   Library to communicate with MWA devices via SNMP.
   
   Create an instance of class 'SNMP' and call 'getCmd' and 'setCmd' methods.

""" 

import socket
import logging
import traceback

globlogger = logging.getLogger('SNMP')

import pysnmp
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.proto import rfc1902

class SNMP:
  def __init__(self, host=None, port=161, user='', password='', community='public', logger=None):
    if not host:
      raise ValueError,"No hostname provided"
    if logger:
      self.logger = logger
    else:
      self.logger = globlogger
    try:
      if user and password:    #V3 protocol
        self.auth = cmdgen.UsmUserData(user, authKey=password, authProtocol=cmdgen.usmHMACSHAAuthProtocol)
        self.dest = cmdgen.UdpTransportTarget((host, port))
      else:
        self.auth = cmdgen.CommunityData(community,community)
        self.dest = cmdgen.UdpTransportTarget((host, port))
    except pysnmp.error.PySnmpError:
      self.logger.critical("SNMP exception in __init__: %s" % traceback.format_exc())
    except socket.error:
      self.logger.critical("Socket exception in __init__: %s" % traceback.format_exc())


  def getCmd(self, *varBinds):
    """Wraps the 'getCmd' function to save typing, and print any error messages, if present.

    Arguments:
      *varBinds - one or more SNMP numeric target tuples

    Returns:
      varBinds - a list of tuples, each composed of an ObjectName object and its value as an rfc1902 data type instance
    """
    try:
      errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(self.auth,self.dest,*varBinds)
    except pysnmp.error.PySnmpError:
      self.logger.critical("SNMP exception in getCmd: %s" % traceback.format_exc())
      return []
    if errorIndication:
      self.logger.error("SNMP Transport error in getCmd: %s" % errorIndication)
      return []
    if int(errorStatus) <> 0:
      self.logger.error("SNMP protocol error in getCmd: %s" % errorStatus.prettyPrint())
      self.logger.error("  Error in object %d: %s" % (errorIndex-1, varBinds[errorIndex-1]))
      return []
    return varBinds

  def setCmd(self, *varBinds):
    """Wraps the 'setCmd' function to save typing, and print any error messages, if present.

    Arguments:
      *varBinds - one or more variables to assign, each of which is a tuple consisting of an SNMP numeric target tuple, and a 
                  value to set it to, encoded as an rfc1902 data type instance.

    Returns:
      varBinds - a list of tuples, each composed of an ObjectName object and its value as an rfc1902 data type instance.
                 These are the names and new value/s of the variables assigned.
    """
    try:
      errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().setCmd(self.auth,self.dest,*varBinds)
    except pysnmp.error.PySnmpError:
      self.logger.critical("SNMP exception in getCmd: %s" % traceback.format_exc())
      return []
    if errorIndication:
      self.logger.error("SNMP Transport error in setCmd: %s" % errorIndication)
      return []
    if int(errorStatus) <> 0:
      self.logger.error("SNMP protocol error in setCmd: %s" % errorStatus.prettyPrint())
      self.logger.error("  Error in object %d: %s" % (errorIndex-1, varBinds[errorIndex-1]))
      return []
    return varBinds

  def bulkCmd(self, N, M, *varNames):
    """Wraps the 'bulkCmd' function to save typing, and print any error messages, if present.

    Arguments:
      N - how many of *varNames passed in request should be queried for a single instance within a request.
      M - how many instances of Managed Objects in the rest of *varNames, besides first nonRepeaters ones,
          should be queried with single request. 
      *varNames - one or more SNMP numeric target tuples

      (if the above descriptions for N and M sound cryptic, it's because I don't know what they do either - that's
       cut and pasted from the pysnmp docs)

    Returns:
      varBinds - a list of tuples, each composed of an ObjectName object and its value as an rfc1902 data type instance
    """
    try:
      errorIndication, errorStatus, errorIndex, varBinds = cmdgen.CommandGenerator().bulkCmd(self.auth,self.dest,N,M,*varNames)
    except pysnmp.error.PySnmpError:
      self.logger.critical("SNMP exception in getCmd: %s" % traceback.format_exc())
      return []
    if errorIndication:
      self.logger.error("SNMP Transport error in bulkCmd: %s" % errorIndication)
      return []
    if int(errorStatus) <> 0:
      self.logger.error("SNMP protocol error in bulkCmd: %s" % errorStatus.prettyPrint())
      self.logger.error("  Error in object %d: %s" % (errorIndex-1, varNames[errorIndex-1]))
      return []
    return varBinds

  def get(self, arg):
    if type(arg) == tuple:
      res = self.getCmd(arg)
      if res:
        return res[0][1]
      else:
        return None 
    elif type(arg) == dict:
      res = self.getCmd(*arg.values())
      if not res:
        return None
      else:
        resdict = {}
        argR = dict(zip(arg.values(),arg.keys()))   #Invert the arg dict, so address tuples are keys, and field names are values
        for add,val in res:
          resdict[argR[tuple(add)]] = val
        return resdict

