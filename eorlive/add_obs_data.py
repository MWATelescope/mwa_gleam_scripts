import urllib2,urllib,simplejson,sys,httplib,json,pickle,psycopg2,os,traceback
from mwapy.ephem_utils import GPSseconds_now
from datetime import datetime

fusionname='/nfs/blank/h4215/aaronew/MWA_Tools/eorlive/FConn.p'
client_id='1059126630788.apps.googleusercontent.com'
redirect_uri='http://localhost'
client_secret='Gvj8cXWeowwHuFBtJCCaa2Ry'
api_key='AIzaSyBktkXh2A4xPv4W1aEY6E3Bm1PcQr64pk4'
table_id='1UspWE7G7ccKncYTUbEkpSaSitomsN-7vLkNdx-I'
host='eor-db.mit.edu'
dbname='mwa'
user='mwa'
password='BowTie'
logfile='/nfs/blank/h4215/aaronew/MWA_Tools/eorlive/FusionConnect.log'

class FusionConnector():
    #initialization should only be run once. A pickled instance of FusionConnector will be used to automatically update the google fusion table
    def __init__(self):
        self.client_id=client_id
        self.redirect_uri=redirect_uri
        self.client_secret=client_secret
        self.api_key=api_key
        self.tableid=table_id
        self.dbname=dbname
        self.user=user
        self.host=host
        self.password=password
        self.log_file=logfile

        print 'Visit the URL below in a browser to authorize'
        print '%s?client_id=%s&redirect_uri=%s&scope=%s&response_type=code' % \
            ('https://accounts.google.com/o/oauth2/auth',
             self.client_id,
             self.redirect_uri,
             'https://www.googleapis.com/auth/fusiontables')


        auth_code = raw_input('Enter authorization code (parameter of URL): ')

        data = urllib.urlencode({
                'code':auth_code,
                'client_id':self.client_id,
                'client_secret':self.client_secret,
                'redirect_uri':self.redirect_uri,
                'grant_type': 'authorization_code'
                })
        request = urllib2.Request(
            url='https://accounts.google.com/o/oauth2/token',
            data=data)
        request_open = urllib2.urlopen(request)
        response = request_open.read()
        request_open.close()
        tokens = json.loads(response)
        self.access_token = tokens['access_token']
        self.refresh_token = tokens['refresh_token']
        
    def write_log(self,message):
        nowtime = datetime.now()
        logfile=open(self.log_file,'a')
        logfile.write(nowtime.isoformat()+' : '+message+'\n')
        logfile.close()
        

    #refreshes the access token. Should only be called after failing a check_token
    def get_new_token(self):
        self.write_log('Requesting New Access Token')
        data=urllib.urlencode({'client_id':self.client_id,
                               'client_secret':self.client_secret,
                               'refresh_token':self.refresh_token,
                               'grant_type':'refresh_token'})
        request = urllib2.Request(url='https://accounts.google.com/o/oauth2/token',data=data)
        request_open=urllib2.urlopen(request)
        response=request_open.read()
        request_open.close()
        tokens=json.loads(response)
        access_token=tokens['access_token']
        nowtime=datetime.now()
        self.write_log('Got New Access Token')
        self.access_token=access_token
        
    def is_expired(self):
        self.write_log('Checking Access Token')
        data=urllib.urlencode({'access_token':self.access_token})
        request=urllib2.Request(url="https://www.googleapis.com/oauth2/v1/tokeninfo",data=data)
        request_open=urllib2.urlopen(request)
        response=request_open.read()
        request_open.close()
        expire_info=json.loads(response)
        expire_info=expire_info['expires_in']
        #if token is not expired return true
        self.write_log('Current Token Expires in '+str(expire_info)+' sec')
        if(expire_info>0):
            return False
        else:
            return True


    def send_fusion_query(self,method,query,headers):
        if(self.is_expired()):
            self.get_new_token()
        request=httplib.HTTPSConnection('www.googleapis.com')
        sqlcmd='/fusiontables/v1/query?%s'%(urllib.urlencode({'access_token':self.access_token,'sql':query}))
        self.write_log('Sending Fusion Command : '+sqlcmd)
        request.request(method,sqlcmd,headers=headers)
        response=request.getresponse()
        self.write_log(str(response.status)+' '+response.reason)
        
        

    def send_eor_query(self,query):
        try:
            eorconn = psycopg2.connect(database=self.dbname,user=self.user,password=self.password,host=self.host)
            self.write_log('Successfully Connected to eor-db')
            cur=eorconn.cursor()
        except Exception, e:
            estr= str(e)
            self.write_log('Error Connecting to Database: '+estr)
            exit()
        try:
            cur.execute(query)
            self.write_log('Sucessfully Executed Query: '+query)
            return cur.fetchall()
        except Exception, e:
            estr=str(e)
            self.write_log('Error executing db query: '+query+' Exception: '+estr)
            exit()
        


    def insert_times(self):
     
   #first add up all observation times
        nowtime=GPSseconds_now()
        rows=self.send_eor_query('select starttime, stoptime from mwa_setting where projectid=\'G0009\' and stoptime<'+str(nowtime))
        totsecs=0.
        for row in rows:
            totsecs=totsecs+row[1]-row[0]
        tothours=totsecs/3600.
        nowtime=datetime.utcnow()
        query='INSERT INTO %s (Date,TotObsTime) VALUES (\'%s\',%s)'%(self.tableid,nowtime.isoformat(),str(tothours))
        self.send_fusion_query('POST',query,{'Content-Length':0})
        
        
if __name__=='__main__':
    if(not(os.path.isfile(fusionname))):
        fuser = FusionConnector()
        pickle.dump(fuser,open(fusionname,'wb'))
    else:
        fuser=pickle.load(open(fusionname,'rb'))
    fuser.insert_times()
    pickle.dump(fuser,open(fusionname,'wb'))

        
