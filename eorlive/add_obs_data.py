#!/usr/bin/env python
import urllib2,urllib,simplejson,sys,httplib,json,pickle,psycopg2,os,traceback,re,subprocess,time
from mwapy.ephem_utils import GPSseconds_now
from datetime import datetime
import numpy as np
n_d = 2 
update_d_all=False
fusionname='/nfs/blank/h4215/aaronew/MWA_Tools/eorlive/FConn.p'
client_id='1059126630788.apps.googleusercontent.com'
redirect_uri='http://localhost'
client_secret='Gvj8cXWeowwHuFBtJCCaa2Ry'
api_key='AIzaSyBktkXh2A4xPv4W1aEY6E3Bm1PcQr64pk4'
table_id='1UspWE7G7ccKncYTUbEkpSaSitomsN-7vLkNdx-I'
daytable_id='1EsSh3vXtsPScjZdN2rW5WXL38PWG_g7dFAKQf34'
obstable_id='1poo8vJn8FHcwuZ0OlF-IGpOY5krFvOH-dSZIyPc'
host='eor-db.mit.edu'
fail_log='/nfs/blank/h4215/aaronew/MWA_Tools/eorlive/fail_cmd.log'
hostcurtin='ngas01.ivec.org'
dbname='mwa'
user='mwa'
password='BowTie'
logfile='/nfs/blank/h4215/aaronew/MWA_Tools/eorlive/FusionConnect.log'
int_min="240"

def write_fail_log(message):
    nowtime=datetime.now()
    logfile=open(fail_log,'a')
    logfile.write(nowtime.isoformat(' ')+' : '+message+'\n')
    logfile.close()

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
        while((int(response.status)==403 or int(response.status==503))):
                    #sleep for ten seconds if 403, than try again
            print str(response.status)+'encountered, waiting 5 seconds, than trying again'
            time.sleep(5)
            if(self.is_expired()):
                self.get_new_token()
            request=httplib.HTTPSConnection('www.googleapis.com')
            sqlcmd='/fusiontables/v1/query?%s'%(urllib.urlencode({'access_token':self.access_token,'sql':query}))
            self.write_log('Sending Fusion Command : '+sqlcmd)
            request.request(method,sqlcmd,headers=headers)
            response=request.getresponse()
            self.write_log(str(response.status)+' '+response.reason)
        return response
    
    def get_mit_filelist(self):
        request=urllib2.Request(url='http://eor-02.mit.edu:7777/QUERY?query=files_list&format=list')
        request_open=urllib2.urlopen(request)
        response=request_open.read()
        request_open.close()
        return iter(response.splitlines())
        #iterate through all obserations at MIT, check obsid in data base to see if observation is G0009

    def get_mit_download_time(self):
        #now iterate through obsid list check if data data is G0009 and find observation time
        tottime=0.
        #build a dictionary
        rows_g9 = self.send_eor_query('select starttime, stoptime, projectid from mwa_setting where projectid=\'G0009\'')
        for row in rows_g9:
            conn=psycopg2.connect(database='ngas',user='ngas_ro',host='ngas.mit.edu',password='ngas$ro')
            obsid=str(int(row[0]))
            print obsid
            cur=conn.cursor()
            cur.execute("SELECT file_id,file_version,ngas_files.disk_id,ngas_disks.host_id FROM ngas_files INNER JOIN ngas_disks ON ngas_files.disk_id = ngas_disks.disk_id where ngas_files.file_id LIKE %s",['%'+str(obsid)+'%'])
            rows=cur.fetchall()
            #check for duplicates
            file_list=[]
            for frow in rows:
                if(not(frow[0] in file_list)):
                    file_list.append(frow[0])
            print len(rows)
            print len(file_list)
            print tottime
            nfiles=self.send_eor_query('select count(*) from (select observation_num from data_files where observation_num='+str(obsid)+') as foo;')[0][0]
            print nfiles
            if(nfiles>0):
                tottime+=float(len(file_list))/float(nfiles)*(row[1]-row[0])
        return tottime/3600.
    
    def get_fail_rates(self):
        gps_cmd = self.send_eor_query("select gpsnow()")
        try:
            gps_use=str(gps_cmd[0][0])
        except Exception,e:
            self.write_log("Error getting current gps time : "+str(e))
            gps_use="gpsnow()"
        query = "select count(*) from (select distinct on (observation_number) observation_number, mode from obsc_mwa_setting where observation_number >("+gps_use+"-"+int_min+"*60) and observation_number <("+gps_use+"-30) and mode!='standby' ) as foo"
        write_fail_log('Executing query total commands: '+query)
        quarter_hour_cmds=self.send_eor_query(query)
        cmd_count=0.
        write_fail_log('Executing query total commands: '+query)
        try:
            quarter_hour_cmds=quarter_hour_cmds[0]
            cmd_count=quarter_hour_cmds[0]
        except Exception,e:
            self.write_log("Error getting total command counts : "+str(e))
        fail_rates=range(0,16)
        for rx in range(1,17):

            query="select count(*) from (select distinct on (rr.observation_number,rx_state_good) rr.observation_number from recv_readiness rr inner join obsc_mwa_setting oc on rr.observation_number=oc.observation_number where rr.rx_id="+str(rx)+" and rr.observation_number > ("+gps_use+"-"+int_min+"*60) and rr.observation_number < ("+gps_use+"-30) and oc.mode!='standby' and rr.all_good='t') as foo"
            write_fail_log('Executing query on Rx '+str(rx)+': '+query)
            good_cmds=self.send_eor_query(query)

            try:
                fail_rates[rx-1]=1.-float(good_cmds[0][0])/float(cmd_count)
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

    def get_n_data(self,obsid):
        loccmd = 'python /csr/mwa/python/mwa_git/mwatools_setup/bin/obslocate.py -s eor-db.mit.edu -r ngas01.ivec.org -o '+str(obsid)
        p=subprocess.Popen([loccmd,],stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
        outstr = p.communicate()
        print outstr
        ncur = 0
        nmit = 0
        ecur = 0
        emit = 0
        print outstr
        curstr=outstr[0]
        print '\n'
        print curstr
        fmatch = re.compile(' [0-9]{1,2}')
        nmatch=0
        matches=fmatch.findall(curstr)
        nmatch=len(matches)
        print 'matches:'
        print matches
        for match in matches:
            ncur = ncur+int(match)
        if(nmatch==0):
            ecur=1
        loccmd = 'python /csr/mwa/python/mwa_git/mwatools_setup/bin/obslocate.py -s eor-db.mit.edu -r eor-02.mit.edu -o '+str(obsid)
        p=subprocess.Popen([loccmd,],stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
        outstr = p.communicate()
        print outstr
        mitstr=outstr[0]
        print '\n'
        print mitstr
        fmatch = re.compile('eor-[0-9]{2}.mit.edu [0-9]{1,2}')
        matches=fmatch.findall(mitstr)
        nmatch=len(matches)
        print 'matches:'
        print matches
        for match in matches:
            nmatch = re.compile(' [0-9]{1,2}')
            nn=nmatch.search(match)
            nmit+=int(match[nn.start()+1:nn.end()])
        if(nmatch==0):
            emit=0
        print ncur
        print nmit
        return (nmit,emit,ncur,ecur)
        
    def check_mit(self,obsid):
        query = 'SELECT MITData, MROData FROM %s where ObsID=%s'%(obstable_id,obsid)
        response=self.send_fusion_query('GET',query,{})
        response = json.loads(response.read())
        try:
            fusionrows=response['rows']
        
            nmit = int(fusionrows[0][0])
            nmro = int(fusionrows[0][1])
        
            if(nmit==nmro):
                return 1
            else:
                return 0
        except Exception, e:
            print 'Observation Number Invalid'

    def read_uvfits_loc(self,obsid):
        query = 'SELECT UVFITS_Files FROM %s where ObsID=%s'%(obstable_id,obsid)
        response=self.send_fusion_query('GET',query,{})
        response = json.loads(response.read())
        try:
            fusionrows=response['rows']
            return fusionrows[0][0]
        except Exception, e:
            print 'Observation Number Invalid'

            
            

    def check_obs(self):
        #get list of all G009 mwa_setting entries
        #retrieve entire fusion table
        #get all g0009 observations
        rows=self.send_eor_query('select observation_number,obsname,starttime,stoptime,dec_phase_center from obsc_mwa_setting where projectid=\'G0009\' order by observation_number desc')
        self.write_log('deleting observations table')
        query = 'SELECT ObsID,MROData,CurtinData,MITData,ROWID,Dec,ObsName FROM %s'%(obstable_id)
        response= self.send_fusion_query('GET',query,{})
        #load the table
        #print response.read()
        response=json.loads(response.read())
        fusionrows = response['rows']
        #add rows to everything
        fusion_obsids = []
        fusion_decs=[]
        fusion_obsnames=[]
        fusion_curtindata = []
        fusion_mitdata = []
        fusion_mrodata = []
        fusion_rowids = []
        for row in fusionrows:
            fusion_obsids.append(int(row[0]))
            if(not(row[1]=='NaN')):
                fusion_mrodata.append(int(row[1]))
            else:
                fusion_mrodata.append(0)
            if(not(row[2]=='NaN')):
                fusion_curtindata.append(int(row[2]))
            else:
                fusion_curtindata.append(0)
            if(not(row[3]=='NaN')):
                fusion_mitdata.append(int(row[3]))
            else:
                fusion_mitdata.append(0)
            fusion_decs.append(row[5])
            fusion_obsnames.append(row[6])
            fusion_rowids.append(row[4])
        #now go through all g0009 observations and process each row
        
        nupdate = 0
        nnew =0
        updaterows=[]
        #remove duplicates
        used_ids = []
        mm=0
        for obsid in fusion_obsids:
            if(not(obsid in used_ids)):
                used_ids.append(obsid)
            else:
                query = 'DELETE FROM %s WHERE ROWID = \'%s\''%(obstable_id,fusion_rowids[mm])
                response=self.send_fusion_query('POST',query,{'Content-Length':0})
                print response.status, response.reason
            mm=mm+1

            
            
        for row in rows:
            #if the obsid is not in the fusion rows than get date, get number of files at MIT and Curtin
            if(not(int(row[0]) in fusion_obsids) and not(int(row[0]) in used_ids)):
                obsdate=self.send_eor_query('select timestamp_gps('+str(row[0])+')')
                #find number of files at MRO
                nmro=self.send_eor_query('select count(*) from (select observation_num from data_files where observation_num='+str(int(row[0]))+') as foo;')[0][0]
                #find number of files at MIT and Curtin
                (nmit,emit,ncur,ecur)=self.get_n_data(int(row[0]))
                print 'number,MIT: '+str(nmit)
                print 'Error MIT:' + str(emit)
                print 'number Curtin: '+str(ncur)
                print 'Error Curtin: '+str(ecur)
                
                query = 'INSERT INTO %s (ObsDate,ObsID,ObsName,Dec,MROData,CurtinData,MITData,MIT_Error,Curtin_Error,Duration) VALUES (\'%s\',%s,\'%s\',%s,%s,%s,%s,%s,%s,%s)'%(obstable_id,obsdate[0][0].isoformat(),str(row[0]),str(row[1]),str(row[4]),str(nmro),str(ncur),str(nmit),str(emit),str(ecur),str(int(row[3])-int(row[2])))
                response=self.send_fusion_query('POST',query,{'Content-Length':0})
                print response.status,response.reason
                #check of the number of fils at MIT or Curtin are less than the number of files at the MRO
                nnew=nnew+1
            else:
                updaterows.append(row) #if the observation has already been recorded, push and update stats late.
        for row in updaterows:
            obsind = fusion_obsids.index(int(row[0]))
            print 'Line\n'
            print obsind
            print row[1]
            print row[4]
            if(0==len(str(fusion_obsnames[obsind]))):
                print 'Updating ObsName'
                query='UPDATE %s \nSET ObsName=\'%s\' \nWHERE ROWID=\'%s\''%(obstable_id,str(row[1]),str(fusion_rowids[obsind]))
                response=self.send_fusion_query('POST',query,{'Content-Length':0})
            nupdate+=1
            if('NaN'==fusion_decs[obsind]):
                if(row[4] is None):
                    dec = -9999.9999
                else:
                    dec=row[4]
                print 'Updating Dec'
                query='UPDATE %s \nSET Dec=%s\nWHERE ROWID=\'%s\''%(obstable_id,str(dec),str(fusion_rowids[obsind]))
                response=self.send_fusion_query('POST',query,{'Content-Length':0})
            if(not(fusion_mrodata[obsind]==fusion_mitdata[obsind])):# and fusion_curtindata[obsind]==fusion_mrodata[obsind])):

                nmro = self.send_eor_query('select count(*) from (select observation_num from data_files where observation_num='+str(fusion_obsids[obsind])+') as foo;')[0][0]
                print 'UPDATING!'
                (nmit,emit,ncur,ecur)=self.get_n_data(int(row[0]))
                print 'number,MIT: '+str(nmit)
                print 'Error MIT:' + str(emit)
                print 'number Curtin: '+str(ncur)
                print 'Error Curtin: '+str(ecur)
                query = 'UPDATE %s\nSET MROData=%s,CurtinData=%s,Curtin_Error=%s,MIT_Error=%s\nWHERE ROWID=\'%s\''%(obstable_id,str(nmro),str(ncur),str(ecur),str(emit),fusion_rowids[obsind])
                response=self.send_fusion_query('POST',query,{'Content-Length':0})
                    #only update mit data if there are no errors for mit query
                if(not(emit)):
                    query = 'UPDATE %s \nSET MITData=%s\nWHERE ROWID=\'%s\''%(obstable_id,str(nmit),fusion_rowids[obsind])
                    response=self.send_fusion_query('POST',query,{'Content-Length':0})
                    print response.status,response.reason
            return (nnew,nupdate)
#first, get a list of files 



    def insert_data(self):     
        fail_rates=self.get_fail_rates()
        query = 'SELECT Duration FROM %s WHERE UVFITS_Files=1'%(obstable_id)
        response=self.send_fusion_query('GET',query,{})
       # print response.status,response.reason
        response=json.loads(response.read())
        response=response['rows']
        print response
        for mm in range(len(response)):
            response[mm]=float(response[mm][0])
        response=np.array(response)
        print response
        uvtime=round(np.sum(response)/3600,4)

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
        fmt = '%Y-%m-%d %H:%M:%S'
        #update all of the derivative entries retroactively 
        if(update_d_all):
            print 'This should not be happening!'
            query = 'SELECT Hours_Scheduled,Hours_Observed,Hours_At_MIT,ROWID,Date FROM %s ORDER BY Date ASC'%(self.tableid)
            response=self.send_fusion_query('GET',query,{})#get all rows
            print response.status,response.reason
            response=json.loads(response.read())
            fusionrows=response['rows']
            for mm in range(n_d,len(fusionrows)):
                print fusionrows[mm-n_d][4][:19]
                print fusionrows[mm][4][:19]
                time1=datetime.strptime(fusionrows[mm-n_d][4][:19],fmt)
                time2=datetime.strptime(fusionrows[mm][4][:19],fmt)
                dt = (time2-time1).seconds/3600.
                print dt
                dmit = round((float(fusionrows[mm][2])-float(fusionrows[mm-n_d][2]))/dt,4)
                dsch = round((float(fusionrows[mm][0])-float(fusionrows[mm-n_d][0]))/dt,4)
                dobs = round((float(fusionrows[mm][1])-float(fusionrows[mm-n_d][1]))/dt,4)
                print dmit
                query='UPDATE %s \nSET D_Hours_Scheduled=%s,D_Hours_At_MIT=%s,D_Hours_Observed=%s\nWHERE ROWID=\'%s\''%(self.tableid,str(dsch),str(dmit),str(dobs),fusionrows[mm][3])
                response=self.send_fusion_query('POST',query,{'Content-Length':0})
                print mm
                print response.status,response.reason
        #get the previous number of hours to compute dhours/dt
        query = 'SELECT Hours_Scheduled,Hours_Observed,Hours_At_MIT,Date FROM %s ORDER BY Date DESC LIMIT 20'%(self.tableid)
        response=self.send_fusion_query('GET',query,{})
        response = json.loads(response.read())
        fusionrow = response['rows']
        dsched=fusionrow[n_d-1][0]
        dobs = fusionrow[n_d-1][1]
        dmit = fusionrow[n_d-1][2]
        dt=datetime.strptime(fusionrow[n_d-1][3][:19],fmt)
        dt = (datetime.now()-dt).seconds/3600.
        nowtime=datetime.utcnow()
        #get the total number of hours converted to uvfits
        #convert to hours/min
        dsched = round((totschhours-dsched)/dt,4)
        dobs = round((totobshours-dobs)/dt,4)
        dmit = round((hours_at_mit-dmit)/dt,4)
        
        query='INSERT INTO %s (Date,Hours_Observed,Hours_Scheduled,Hours_At_MIT,RxFail1,RxFail2,RxFail3,RxFail4,RxFail5,RxFail6,RxFail7,RxFail8,RxFail9,RxFail10,RxFail11,RxFail12,RxFail13,RxFail14,RxFail15,RxFail16,D_Hours_Observed,D_Hours_Scheduled,D_Hours_At_MIT,Hours_UVFITS) VALUES (\'%s\',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'%(self.tableid,nowtime.isoformat(' '),str(totobshours),str(totschhours),str(hours_at_mit),str(fail_rates[0]),str(fail_rates[1]),str(fail_rates[2]),str(fail_rates[3]),str(fail_rates[4]),str(fail_rates[5]),str(fail_rates[6]),str(fail_rates[7]),str(fail_rates[8]),str(fail_rates[9]),str(fail_rates[10]),str(fail_rates[11]),str(fail_rates[12]),str(fail_rates[13]),str(fail_rates[14]),str(fail_rates[15]),str(dsched),str(dobs),str(dmit),str(uvtime))
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
        f = open('/nfs/blank/h4215/aaronew/MWA_Tools/eorlive/last_obs_start.log','w')
        nowtime=datetime.now()
        f.write(nowtime.isoformat(' '))
        f.close()
        f = open('/nfs/blank/h4215/aaronew/MWA_Tools/eorlive/obs_update.log','a')
        f.write(nowtime.isoformat(' ')+' : starting\n')
        f.close()
        (nnew,nupdate)=fuser.check_obs()
        f = open('/nfs/blank/h4215/aaronew/MWA_Tools/eorlive/last_obs_stop.log','w')
        nowtime=datetime.now()
        f.write(nowtime.isoformat(' '))
        f.close()
        f=open('/nfs/blank/h4215/aaronew/MWA_Tools/eorlive/obs_update.log','a')
        f.write(nowtime.isoformat(' ')+' : finished with '+str(nnew)+' new entries and '+str(nupdate)+' updates\n')
        f.close()

    pickle.dump(fuser,open(fusionname,'wb'))
        
