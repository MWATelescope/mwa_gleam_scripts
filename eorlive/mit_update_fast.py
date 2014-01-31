#!/usr/bin/env python



from add_obs_data import *
import numpy,time


logfile='/nfs/blank/h4215/aaronew/mit_update_fast.log'
#checks if there are less than 2 instances of num in numlist (assume num>0)
def l2(num,numlist):
    mm=0
    for kk in range(0,len(numlist)):
        if(numlist[kk]==num):
            mm+=1
            print mm
    if(mm<2):
        return True
    else:
        return False
    

def update_mit_counts(fconn):
        """
    request=urllib2.Request(url='http://eor-02.mit.edu:7777/QUERY?query=files_list&format=list')
    request_open=urllib2.urlopen(request)
    response=request_open.read()
    request_open.close()
    obs_iter=iter(response.splitlines())
    #now build a  dictionary with every observation file 
    obs_dict = {}
    gpure=re.compile('gpubox[0-9]{2}')
    obsre=re.compile('/[0-9]{10}_')
    for line in obs_iter:
        gpu_str=gpure.search(line)
        obs_str=obsre.search(line)
        if(obs_str and gpu_str):
            obsnum = int(line[obs_str.start()+1:obs_str.end()-1])
            gpunum = int(line[gpu_str.end()-2:gpu_str.end()])
            print gpunum
            print obsnum

            if(str(obsnum) in obs_dict.keys()):
                tlist = obs_dict[str(obsnum)]
                if(l2(gpunum,obs_dict[str(obsnum)]) and gpunum <=24 and gpunum>=0):
                    #if gpu box file not in list of files for that obs, add it 
                    obs_dict[str(obsnum)].append(gpunum)
            else:
                obs_dict[str(obsnum)]=[gpunum]
    #now update mit counts
    """
        query = 'SELECT ObsID,MITData,MROData,ROWID FROM %s'%(obstable_id) 
        response=fconn.send_fusion_query('GET',query,{})
        response = json.loads(response.read())
        fusionrows=response['rows']
        numSuccess=0
    
        for row in fusionrows:
            if(not(int(row[1])==int(row[2]))):
                print row[1], row[2]
                conn=psycopg2.connect(database='ngas',user='ngas_ro',host='ngas.mit.edu',password='ngas$ro')
                obsid=str(int(row[0]))
                print obsid
                cur=conn.cursor()
                cur.execute("SELECT file_id,file_version,ngas_files.disk_id,ngas_disks.host_id FROM ngas_files INNER JOIN ngas_disks ON ngas_files.disk_id = ngas_disks.disk_id where ngas_files.file_id LIKE %s",['%'+str(obsid)+'%'])
                rows=cur.fetchall()
                file_list=[]
                for frow in rows:
                    if(not(frow[0] in file_list)):
                        file_list.append(frow[0])
                print len(file_list)
                query='UPDATE %s \n SET MITData=%s\nWHERE ROWID=\'%s\''%(obstable_id,str(len(file_list)),str(row[3]))
                response=fconn.send_fusion_query('POST',query,{'Content-Length':0})
                print response.status, response.reason
                if(int(response.status)==200):
                    numSuccess=numSuccess+1
                f = open(logfile,'a')
                f.write(datetime.now().isoformat(' ')+' : '+'sucessfully ran update with '+str(numSuccess)+' good entries \n')
                f.close()

if __name__=='__main__':
    if(not(os.path.isfile(fusionname))):
        fuser=FusionConnector()
        pickle.dump(fuser,open(fusionname,'wb'))
    else:
        fuser=pickle.load(open(fusionname,'rb'))
    update_mit_counts(fuser)


        
            

                
                
