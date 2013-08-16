import urllib2,urllib,simplejson,sys,httplib,json,pickle,psycopg2,os,traceback,re
from mwapy.ephem_utils import GPSseconds_now
from datetime import datetime

fusionname='/nfs/blank/h4215/aaronew/MWA_Tools/eorlive/FConn.p'
client_id='1059126630788.apps.googleusercontent.com'
redirect_uri='http://localhost'
client_secret='Gvj8cXWeowwHuFBtJCCaa2Ry'
api_key='AIzaSyBktkXh2A4xPv4W1aEY6E3Bm1PcQr64pk4'
table_id='1UspWE7G7ccKncYTUbEkpSaSitomsN-7vLkNdx-I'
obstable_id='1poo8vJn8FHcwuZ0OlF-IGpOY5krFvOH-dSZIyPc'
host='eor-db.mit.edu'
hostcurtin='ngas01.ivec.org'
dbname='mwa'
user='mwa'
password='BowTie'
logfile='/nfs/blank/h4215/aaronew/MWA_Tools/eorlive/FusionConnect.log'
int_min="20"
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
        logfile.write(nowtime.isoformat(' ')+' : '+message+'\n')
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
        pickle.dump(self,open(fusionname,'wb'))

    def is_expired(self):
        self.write_log('Checking Access Token')
        access_token=self.access_token
        data=urllib.urlencode({'access_token':access_token})
        request=urllib2.Request(url='https://www.googleapis.com/oauth2/v1/tokeninfo',data=data)
        try:
            request_open=urllib2.urlopen(request)
            response=request_open.read()
            request_open.close()
            expire_info=json.loads(response)
            expire_info=expire_info['expires_in']
        #if token is not expired return true
            self.write_log('Current Token Expires in '+str(expire_info)+' sec')
            return False
        except: 
            self.write_log('Token Expired')
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
    
    def get_mit_filelist(self):
        request=urllib2.Request(url='http://eor-02.mit.edu:7777/QUERY?query=files_list&format=list')
        request_open=urllib2.urlopen(request)
        response=request_open.read()
        request_open.close()
        return iter(response.splitlines())
        #iterate through all obserations at MIT, check obsid in data base to see if observation is G0009

    def get_mit_download_time(self):
        request=urllib2.Request(url='http://eor-02.mit.edu:7777/QUERY?query=files_list&format=list')
        request_open=urllib2.urlopen(request)
        response=request_open.read()
        request_open.close()
        lineiterator=iter(response.splitlines())
        #iterate through all obserations at MIT, check obsid in data base to see if observation is G0009
        #if it is, add total observation seconds to observation time
        p=re.compile('/[0-9]{10}_')
        id_list=[]
        for line in lineiterator:
            m=p.search(line)
            if(m):
                obsid=int(line[m.start()+1:m.end()-1])
                if(not(obsid in id_list)):
                    id_list.append(obsid)
                    id_list.sort()
        #now iterate through obsid list check if data data is G0009 and find observation time
        tottime=0.
        rows_g9 = self.send_eor_query('select starttime, stoptime, projectid from mwa_setting where projectid=\'G0009\'')
        for row in rows_g9:
            if(row[0] in id_list):
                    tottime+=(row[1]-row[0])
            

        return tottime/3600.
    
    def get_fail_rates(self):
        quarter_hour_cmds=self.send_eor_query("select count(*) from (select distinct on (observation_number) observation_number, mode from obsc_mwa_setting where observation_number >(gpsnow()-"+int_min+"*60) and mode!='standby' ) as foo")
        cmd_count=0.
        try:
            quarter_hour_cmds=quarter_hour_cmds[0]
            cmd_count=quarter_hour_cmds[0]
        except Exception,e:
            self.write_log("Error getting total command counts : "+str(e))
        fail_rates=range(0,16)
        for rx in range(1,17):
            good_cmds=self.send_eor_query("select count(*) from (select distinct on (rr.observation_number,rx_state_good) rr.observation_number from recv_readiness rr inner join obsc_mwa_setting oc on rr.observation_number=oc.observation_number where rr.rx_id="+str(rx)+" and rr.observation_number > (gpsnow()-"+int_min+"*60) and oc.mode!='standby' and rr.rx_state_good='t') as foo")
            try:
                fail_rates[rx-1]=1.-good_cmds[0][0]/cmd_count
            except Exception,e:
                fail_rates[rx-1]=0.
                self.write_log("Error computing failure rate : "+str(e))
        return fail_rates
            
            
                                              

    
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
        

    def check_obs(self):
        #get list of all G009 mwa_setting entries
        #for each entry, overwrite fusion table
        obsids = []
        dates = []
        names=[]
        durations=[]
        mrofiles=[]
        mitfiles=[]
        lineiterator=self.get_mit_filelist()
        rows=self.send_eor_query('select observation_number,obsname,starttime,stoptime from obsc_mwa_setting where projectid=\'G0009\'')
        self.write_log('deleting observations table')
        query = 'DELETE FROM %s'%(obstable_id)
        self.send_fusion_query('POST',query,{'Content-Length':0})

        for row in rows:
            obsnum=row[0]
            obsdate=self.send_eor_query('select timestamp_gps('+str(row[0])+')')
            dates.append(obsdate[0])
            durations.append(row[3]-row[2])
            names.append(row[2])
            #find number of files
            files=self.send_eor_query('select count(*) from (select observation_num from data_files where observation_num='+str(obsnum)+') as foo;')
            mrofiles.append(files[0])
            #now get mit files
            p=re.compile('/[0-9]{10}_')
            fcount=0
            print obsnum
            for line in lineiterator:
                m=p.search(line)
                if(m):
                    obsid=int(line[m.start()+1:m.end()-1])
                    if(obsid==int(obsnum)):
                        print obsid, obsnum
                        fcount+=1
            mitfiles.append(fcount)
            print obsdate[0]
            query = 'INSERT INTO %s (ObsDate,ObsID,MROData,MITData,Duration) VALUES (\'%s\',%s,%s,%s,%s)'%(obstable_id,obsdate[0][0].isoformat(),str(obsnum),str(int(files[0][0])),str(fcount),str(row[3]-row[2]))
            #now drop table at 
            self.write_log('sending: '+query)
            self.send_fusion_query('POST',query,{'Content-Length':0})

    def insert_data(self):     
        fail_rates=self.get_fail_rates()
        hours_at_mit=self.get_mit_download_time()
        nowtime=GPSseconds_now()
        rows=self.send_eor_query('select starttime, stoptime from mwa_setting where projectid=\'G0009\' and stoptime<'+str(nowtime))
        totobssecs=0.
        for row in rows:
            totobssecs=totobssecs+row[1]-row[0]
        totobshours=totobssecs/3600.
        nowtime=datetime.utcnow()
        #next add up total scheduled times
        rows=self.send_eor_query('select starttime, stoptime from mwa_setting where projectid=\'G0009\'')
        totschsecs=0.
        for row in rows:
            totschsecs=totschsecs+row[1]-row[0]
        totschhours=totschsecs/3600.
        nowtime=datetime.utcnow()
        query='INSERT INTO %s (Date,Hours_Observed,Hours_Scheduled,Hours_At_MIT,RxFail1,RxFail2,RxFail3,RxFail4,RxFail5,RxFail6,RxFail7,RxFail8,RxFail9,RxFail10,RxFail11,RxFail12,RxFail13,RxFail14,RxFail15,RxFail16) VALUES (\'%s\',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'%(self.tableid,nowtime.isoformat(' '),str(totobshours),str(totschhours),str(hours_at_mit),str(fail_rates[0]),str(fail_rates[1]),str(fail_rates[2]),str(fail_rates[3]),str(fail_rates[4]),str(fail_rates[5]),str(fail_rates[6]),str(fail_rates[7]),str(fail_rates[8]),str(fail_rates[9]),str(fail_rates[10]),str(fail_rates[11]),str(fail_rates[12]),str(fail_rates[13]),str(fail_rates[14]),str(fail_rates[15]))
        self.send_fusion_query('POST',query,{'Content-Length':0})

        
        
if __name__=='__main__':
    if(not(os.path.isfile(fusionname))):
        fuser = FusionConnector()
        pickle.dump(fuser,open(fusionname,'wb'))
    else:
        fuser=pickle.load(open(fusionname,'rb'))
    #parse command line arguments
    mode=sys.argv[1]
    if(int(mode)==0):
        fuser.insert_data()
    else:
        fuser.check_obs()
    pickle.dump(fuser,open(fusionname,'wb'))
        
