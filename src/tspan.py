import time
import string
from datetime import datetime,timedelta,tzinfo

ZERO = timedelta(0)
HR8 = timedelta(hours=8)

# UTC and WAST time zone information classes.

class UTC(tzinfo):
  """UTC"""
  def utcoffset(self, dt):
    return ZERO
  def tzname(self, dt):
    return "UTC"
  def dst(self, dt):
    return ZERO

class WAST(tzinfo):
  def utcoffset(self, dt):
    return HR8
  def tzname(self, dt):
    return "WAST"
  def dst(self, dt):
    return ZERO


tzutc = UTC()
tzwast = WAST()

#Make the default time zone UTC for all time input
tzdefault = tzutc


days = ['MON','TUE','WED','THU','FRI','SAT','SUN']
months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']
mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
mods = ['TOM','YES','TOD','LAS','NEX','THI']

minyear = 1900
maxyear = 2030

#Component parsing functions. Each returns a cleaned-up value if the component passed 
#represents it's target type, otherwise 0 (for integer types) or None (for string types)

def getdayn(s):
  """Parse the name of a weekday. The first three letters must be in 'days'.
  """
  if s.strip()[:3].upper() in days:
    return s.strip()[:3].upper()


def getmod(s):
  """Parse a weekday modifier. The first three letters must be in 'mods'.
  """
  if s.strip()[:3].upper() in mods:
    return s.strip()[:3].upper()


def getday(s, m=1):
  """Parse a day-of-month number, given an optional already-parsed month number.
  """
  try:
    flag = s.strip()[-2:].upper()
    if flag in ['ST','ND','RD','TH']:
      s = s[:-2]
    else:
      flag = ''
    n = int(s)
    if (n>0 and n<mlen[m-1]):
      return n
    else:
      return 0
  except:
    return 0


def getmonthn(s):
  """Parse a month name.
  """
  if s.strip()[:3].upper() in months:
    return s.strip()[:3].upper()


def getmonth(s):
  """Parse a month number.
  """
  try:
    flag = s.strip()[-2:].upper()
    if flag in ['ST','ND','RD','TH']:
      s = s[:-2]
    else:
      flag = ''
    n = int(s)
    if (n>0 and n<13):
      return n
    else:
      return 0
  except:
    return 0


def getyear(s):
  """Parse a year number. Years must be four digit, not two digit.
  """
  try:
    s = s.strip()
    n = int(s)
    if len(s)==2:
      return 0     #Don't accept two digit years
    elif len(s)==4:
      if (n>=minyear) and (n<maxyear):
        return n
      else:
        return 0
    else:
      return 0   #Wrong number of digits
  except:
    return 0


def ishour(s,flag=''):
  """Given a time subcomponent plus an optional trailing 'AM' or 'PM',
     return True if that component represents a valid hour number.
  """
  try:
    n = int(s)
    flag = flag.upper()
    if (flag=='AM') or (flag=='PM'):
      return (n>=1 and n<=12)
    else:
      return (n>=0 and n<=23)
  except:
    return 0


def isminsec(s):
  """Given a time subcomponent plus an optional trailing 'AM' or 'PM',
     return True if that component represents a valid minute or second.
  """
  try:
    s = s.strip()
    n = int(s)
    return (len(s)==2 and n>=0 and n<=59)
  except:
    return 0


def gettime(s):
  """Given a valid time string, return (hr,mn,sc) tuple. Valid times are:
        <hour>AM or <hour>PM
        <hour>:<minute> with optional 'AM' or 'PM'
        <hour>:<minute>:<second> with optional AM or PM
     valid hours are 1-12 with an AM or PM flag, 0-23 otherwise.
  """
  try:
    flag = s.strip()[-2:].upper()
    if flag=='AM' or flag=='PM':
      s = s[:-2]
    else:
      flag = ''
    t = tuple(s.split(':'))
    if (len(t)==1) and flag:
      hr,mn,sc = t[0],'00','00'
    elif len(t)==2:
      hr,mn = t
      sc = '00'
    elif len(t)==3:
      hr,mn,sc = t
    else:
      return None

    if ishour(hr,flag) and isminsec(mn) and isminsec(sc):
      if flag=='PM' and hr<>'12':
        return int(hr)+12, int(mn), int(sc)
      elif ((flag=='AM') and (hr=='12')):
        return 0, int(mn), int(sc)
      else:
        return int(hr), int(mn), int(sc)
      
    else:
      return None
  except:
    return None
    
    
def getdate(s):
  """Given a valid date string, return (yr,mn,dy) tuple. Seperators can be '/' or '-', 
     and the year must be four digits, and between 'minyear' and 'maxyear'. Valid
     date formats are:
          <year>/<month>/<day> or <year>-<month>-<day>
          <day>/<month>/<year> or <day>-<month>-<year>
  """
  try:
    t = s.split('/')
    if len(t) == 3:
      p1,p2,p3 = tuple(map(int,t))
    else:
      t = s.split('-')
      if len(t) == 3:
        p1,p2,p3 = tuple(map(int,t))
      else:
        return None
    if p1>=minyear and p2<=12 and p3<=mlen[p2-1] and p1<=maxyear and p2>=1 and p3>=1:
      yr,mn,dy = p1,p2,p3
    elif p3>minyear and p2<=12 and p1<=mlen[p2-1] and p3<=maxyear and p2>=1 and p1>=1:
      yr,mn,dy = p3,p2,p1
    return yr,mn,dy
  except:
    return None


def getgpssec(s):
  """Given a valid time in seconds since the GPS epoch, return that value as an integer.
     Valid times in this case are any 9 or 10 digit integer.
  """
  try:
    s = s.strip()
    n = int(s)
    if len(s)<9 or len(s)>10:
      return 0     #GPS seconds must be 9 or 10 digits
    else:
        return n
  except:
    return 0
    
    
def gettzone(s):
  """Parse a time zone descriptor, either UTC or WAST, or a few variants of those.
  """
  s = s.strip().upper()
  if s=='UT' or s=='UTC' or s=='GMT':
    return tzutc
  elif s=='WST' or s=='WAST':
    return tzwast
  else:
    return None



def parse(s):
  """Parse a freeform time string, and return either a 'datetime' object representing the given time,
     or an integer representing the number of seconds since the GPS epoch, if that was given instead
     of a date and time. A list of unparsed string components in the time descripter is also returned.
     If empty, the input string was parsed completely, if not, the returned components were not
     recognised, and should be returned to the user in an error message.
     
     The order of the components of the time specifier are very flexible.
     
     Examples of valid times:
     
     12:46AM WAST last thursday
     2pm WAST tomorrow
     2009-9-16 03:45
     23:47 UT july 3rd
     935831132
    
     If a weekday name (eg 'tuesday') is specified, it is assumed to refer to the NEAREST match
     to that day name, before or after 'today', unless modified with 'last', 'this', or 'next'.
     
     If day, month, and/or year is not specified, the current value is used, so an ambiguous string
     like "2pm June" will be taken as 14:00:00 on the Nth day of June in the current year, where
     'N' is the current day of the month.
     
     The default time zone is specified at the top of this module, currently UTC. Time zone (UTC or
     WAST) can be given in the time string. No other time zones are recognised.
  """
  slist = s.split()

  gpssec = None
  time = None
  date = None
  year = None
  monthn = None
  day = None
  month = None
  dayn = None
  mod = None
  tzone = None
  parsed = []
  for sbit in slist:
    gpssec = getgpssec(sbit)
    if gpssec:
      parsed.append(sbit)

  if not gpssec:
    for sbit in slist:
      if not date:
        date = getdate(sbit)
        if date:
          parsed.append(sbit)
      if not time:
        time = gettime(sbit)
        if time:
          parsed.append(sbit)

    for sbit in slist:
      if (not monthn) and (not date):
        monthn = getmonthn(sbit)
        if monthn:
          parsed.append(sbit)
      if (not dayn) and (not date):
        dayn = getdayn(sbit)
        if dayn:
          parsed.append(sbit)
      if (not mod) and (not date):
        mod = getmod(sbit)
        if mod:
          parsed.append(sbit)
      if not tzone:
        tzone = gettzone(sbit)
        if tzone:
          parsed.append(sbit)
      if (not day) and (not date):
        if monthn:
          day = getday(sbit,months.index(monthn)+1)
        else:
          day = getday(sbit)
        if day:
          parsed.append(sbit)
          continue
      if (not month) and (not monthn) and (not date) and day:
        month = getmonth(sbit)
        if month:
          parsed.append(sbit)
          continue
      if (not year) and (not date):
        year = getyear(sbit)
        if year:
          parsed.append(sbit)
          continue

  if not tzone:
    tzone = tzdefault

  tstamp = datetime.now(tz=tzone)
  
  nargs = {}
  nargs['microsecond'] = 0
  nargs['tzinfo'] = tzone

  if time:
    nargs['hour'] = time[0]
    nargs['minute'] = time[1]
    nargs['second'] = time[2]

  if date:
    nargs['year'] = date[0]
    nargs['month'] = date[1]
    nargs['day'] = date[2]
  else:
    if day:
      nargs['day'] = day
    if month:
      nargs['month'] = month
    elif monthn:
      nargs['month'] = months.index(monthn)+1
    if year:
      nargs['year'] = year

  tstamp = tstamp.replace(**nargs)    

  dargs = {}
  if dayn:
    wdnow = tstamp.weekday()
    #Pick CLOSEST matching weekday if given day name, not NEXT matching
    ddelta = days.index(dayn) - wdnow
    if ddelta < -3:
      ddelta += 7
    elif ddelta > 3:
      ddelta -= 7
    if mod=='NEX':
      if ddelta < 0:
        ddelta += 14
      else:
        ddelta += 7
    elif mod=='LAS' and ddelta>=0:
      ddelta -= 7
    elif mod=='THI' and ddelta<0:
      ddelta += 7
    dargs['days'] = ddelta
  else:
    if mod=='TOM':
      dargs['days'] = +1
    elif mod=='YES':
      dargs['days'] = -1
    elif mod=='TOD':
      dargs['days'] = 0
      
  unparsed = []
  for sbit in slist:
    if sbit not in parsed:
      unparsed.append(sbit)
  if gpssec:
    return gpssec, unparsed
  else:
    return (tstamp + timedelta(**dargs)).astimezone(tzdefault), unparsed










