import urllib2,urllib,simplejson,sys,httplib,json

client_id='1059126630788.apps.googleusercontent.com'
client_secret='Gvj8cXWeowwHuFBtJCCaa2Ry'
redirect_uri='http://localhost'
api_key='AIzaSyBktkXh2A4xPv4W1aEY6E3Bm1PcQr64pk4'
tableid='1UspWE7G7ccKncYTUbEkpSaSitomsN-7vLkNdx-I'
code='4/WMVe13o7YWmpIagUYiDP2spDDITI.QnSPEVF4dzUUshQV0ieZDAp6g0ovgAI'
access_token="ya29.AHES6ZTVnUGfT9p0nbUwoS9VjmJ-REkg25Hm8LKm_WQCpQ"
refresh_token='1/Lz1q0mK_SlHIZZ5xSzUXHecoi4TdV_6BGrNLK26Wi4I'
access_token="4/czdiYdxOqGY5S5iOxQ_KJMRK8F5L.0u3a0gjT4pwWshQV0ieZDAp4TwlCgAI"
access_token="ya29.AHES6ZRBZDgOpWCMRSg4x94wxHMU5TI5ZsbdNhyXpVRlZYM"
if __name__=='__main__':
    #    data = '''{"date":"2013-07-08 10:00:00","number":12,tableId":%s}'''%(tableid)
    #   response=self.runRequest("POST","/fusiontables/v1/tables/%s/
    """
    print "copy and paste the url below into browser address bar and hit enter"
    print "https://accounts.google.com/o/oauth2/auth?%s%s%s%s" % \
    ("client_id=%s&" % (client_id),
    "redirect_uri=%s&" % (redirect_uri),
    "scope=https://www.googleapis.com/auth/fusiontables&",
    "response_type=code")
    """
    '''
    data=urllib.urlencode({'code':code,
                           'client_id':client_id,
                           'client_secret':client_secret,
                           'redirect_uri':redirect_uri,
                           'grant_type':'authorization_code'})
    serv_req=urllib2.Request(url='https://accounts.google.com/o/oauth2/token',data=data)
    print serv_req.get_full_url(),serv_req.data
    serv_resp=urllib2.urlopen(serv_req)
    response=serv_resp.read()
    tokens=simplejson.loads(response)
    access_token=tokens['access_token']
    params='?key=%s&access_token=%s'%(api_key,access_token)
    request = httplib.HTTPSConnection('www.googleapis.com')
    request.request('list','/fusiontables/v1/tables/%s/%s'%(tableid,params))
    response=request.getresponse()
    print response.status, response.reason
    response=response.read()
    print response
    '''
    '''
    request = urllib2.Request(url='https://www.googleapis.com/fusiontables/v1/query?%s'%(urllib.urlencode({'access_token': access_token,'refresh_token':refresh_token,
                      'sql': 'SHOW TABLES'})))
			'sql':'insert into 1UspWE7G7ccKncYTUbEkpSaSitomsN-7vLkNdx-I (date,number) VALUES (\'25-07-2013 10:24:45\',2050) '})))
    print request.get_full_url()
    request_open = urllib2.urlopen(request)
    response = request_open.read()
    request_open.close()
    print response
                         
    '''
    '''
    params = "?key=%s&access_token=%s" % (api_key, access_token)
    request = httplib.HTTPSConnection("www.googleapis.com")
    query='INSERT INTO %s (Text,Number,Location,Date) VALUES (\'\',500,\'\',\'2013-07-25 23:35:00\')'%(tableid)
    print query
  #  query = 'SELECT * FROM %s'%(tableid)
    sqlcmd='/fusiontables/v1/query?%s'%(urllib.urlencode({'access_token': access_token,'sql': query}))
    request.request("POST", sqlcmd,headers={'Content-Length':0})
    response = request.getresponse()
    print response.status, response.reason
    '''
    '''
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
    '''

    
    #now check token info
    data=urllib.urlencode({'access_token':access_token})
    request=urllib2.Request(url='https://www.googleapis.com/oauth2/v1/tokeninfo',data=data)
    request_open=urllib2.urlopen(request)
    response=request_open.read()
    request_open.close()
    print response
    
