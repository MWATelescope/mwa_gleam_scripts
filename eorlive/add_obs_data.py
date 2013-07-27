import urllib2,urllib,simplejson,sys,httplib,json,pickle

client_id='1059126630788.apps.googleusercontent.com'
redirect_uri='http://localhost'
secret='Gvj8cXWeowwHuFBtJCCaa2Ry'
api_key='AIzaSyBktkXh2A4xPv4W1aEY6E3Bm1PcQr64pk4'
table_id='1UspWE7G7ccKncYTUbEkpSaSitomsN-7vLkNdx-I'


class FusionConnector():
    #initialization should only be run once. A pickled instance of FusionConnector will be used to automatically update the google fusion table
    def __init__(self):
        self.client_id=client_id
        self.redirect_uri=redirect_uri
        self.secret=secret
        self.api_key=api_key
        self.tableid=tableid
        self.logfile='FusionConnect.txt'
        print '%s?client_id=%s&redirect_uri=%s&scope=%s&response_type=code' % \
            ('https://accounts.google.com/o/oauth2/auth',client_id,redirect_uri,'https://www.googleapis.com/auth/fusiontables')
        request = urllib2.Request(
            url='https://accounts.google.com/o/oauth2/token',
            data=data)
        request_open = urllib2.urlopen(request)
        response = request_open.read()
        request_open.close()
        tokens = json.loads(response)
        self.access_token = tokens['access_token']
        self.refresh_token = tokens['refresh_token']

        auth_code = raw_input('Enter authorization code (parameter of URL): ')

        data = urllib.urlencode({
                'code': auth_code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
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

    #refreshes the access token. Should only be called after failing a check_token
    def get_refresh_token(self):
        data=urllib.urlencode({'client_id':self.client_id,
                               'client_secret':self.client_secret,
                               'refresh_token':self.refresh_token,
                               'grant_type':'refresh_token'})
        request = urllib2.Request(url='https://accounts.google.com/o/oauth2/token',data=data)
        request_open=urllib2.urlopen(request)
        response=request.open.read()
        request_open.close()
        tokens=json.loads(response)
        access_token=tokens['access_tokens']
        self.access_token=access_token
        
    def check_token():
        data=urllib.urlencode({'access_token':self.access_token})
        request=urllib2.Request(url="https://www.googleapis.com/oauth2/v1/tokeninfo?access_token+

    def insert_completed_time(self):
        self.check_token()
        request=httplib.HT


if __name__=='__main__':
    
    request = httplib.HTTPSConnection("www.googleapis.com")
    query='INSERT INTO %s (Text,Number,Location,Date) VALUES (\'\',500,\'\',\'2013-07-25 23:35:00\')'%(tableid)
    print query
  #  query = 'SELECT * FROM %s'%(tableid)
    sqlcmd='/fusiontables/v1/query?%s'%(urllib.urlencode({'access_token': access_token,'sql': query}))
    request.request("POST", sqlcmd,headers={'Content-Length':0})
    response = request.getresponse()
    print response.status, response.reason
    response = response.read()
    print response
    if(response.status==401):
        data = urllib.urlencode({
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'})
        request = urllib2.Request(url='https://accounts.google.com/o/oauth2/token',data=data)
        request_open = urllib2.urlopen(request)
        response = request_open.read()
        request_open.close()
        tokens = json.loads(response)
        access_token = tokens['access_token']
        print access_token
