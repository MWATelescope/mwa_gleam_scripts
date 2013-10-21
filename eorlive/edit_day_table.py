#!/usr/bin/env python

import re
from add_obs_data import *

#************************************************************
#convert the last 7 chars in obsname to julian date (from obs
#table
#************************************************************

def day_from_name(namestr):
    jdsearch = re.compile('[0-9]{7}$')
    jdfind = jdsearch.search(namestr)
    if(jdfind):
        return int(namestr[jdfind.start():jdfind.end()])
    else:
        return 0

#************************************************************
#get the number of hours observed during a julian day
#takes julian_day as argument, along with obstable dict (list of dictionaries)
#returns
#(hours_eor-0,hours_eor-1,hours_eor-2,hours_mro,hours_pawsey,hours_mit,hours_uvfits)
#************************************************************

def get_hours(day_list):
    hours_eor0 = 0.
    hours_eor1 = 0.
    hours_eor2 = 0.
    hours_mit=0.
    hours_paw=0.
    hours_mro=0.
    hours_uvfits=0.
    totsecs = 0.
    for row in day_list:
        hours_mro+=float(row['duration'])
        if(row['dec']==-30.0):
            hours_eor0+=float(row['duration'])
        elif(row['dec']==-27.0):
            hours_eor1+=float(row['duration'])
        elif(row['dec']==-10.0):
            hours_eor2+=float(row['duration'])
        if(row['data_mit']==row['data_mro']):
            hours_mit+=float(row['duration'])
            if(row['uvfits']==1):
                hours_uvfits+=float(row['duration'])
        if(row['data_paw']==row['data_mro']):
            hours_paw+=float(row['duration'])
    return (round(hours_eor0/3600.,2),round(hours_eor1/3600.,2),round(hours_eor2/3600.,2),round(hours_mro/3600.,2),round(hours_paw/3600.,2),round(hours_mit/3600.,2),round(hours_uvfits/3600.,2))


def get_band(obs_name):
    bandsearch=re.compile('^[a-z]{3,4}_')
    bandfind = bandsearch.search(obs_name)
    if(bandfind):
        return obs_name[bandfind.start():bandfind.end()-1]
    else:
        return 'NA'

#************************************************************
#get data and arrange it into a dictionary
#************************************************************
def import_data(fconn):
    fmt = '%Y-%m-%dT%H:%M:%S'
    query = 'SELECT ObsDate, ObsID, ObsName, Dec, MROData, CurtinData, MITData, Duration, UVFITS_Files,ROWID FROM %s'%(obstable_id)
    response = fconn.send_fusion_query('GET',query,{})
    response = json.loads(response.read())
    fusionrows=response['rows']
    data_dict={}
    for row in fusionrows:
        jd = str(day_from_name(str(row[2])))
        if(str(row[8])=='' or str(row[8])=='NaN'):
            row[8]='0'
        if(str(row[6])=='' or str(row[6])=='NaN'):
            row[6]='0'
        if(str(row[4])=='' or str(row[4])=='NaN'):
            row[4]='0'
        if(str(row[5])=='' or str(row[5])=='NaN'):
            row[5]='0'
        temp_dict={'obsdate':datetime.strptime(row[0][:19],fmt),'obsid':int(row[1]),'obsname':str(row[2]),'dec':float(row[3]),'data_mro':int(row[4]),'data_paw':int(row[5]),'data_mit':int(row[6]),'duration':float(row[7]),'uvfits':int(row[8]),'rowid':row[9]}
        if(jd in data_dict.keys()):
            data_dict[jd].append(temp_dict)
        else:
            data_dict[jd]=[temp_dict]
    return data_dict

def update_table(fconn):
    data_dict=import_data(fconn)
    for jd in data_dict.keys():
        update_day(int(jd),data_dict,fconn)

def update_day(julian_day,data_dict,fconn):
    daylist = data_dict[str(julian_day)]
    (hours_eor0,hours_eor1,hours_eor2,hours_mro,hours_pawsey,hours_mit,hours_uvfits)=get_hours(daylist)
    band=get_band(daylist[0]['obsname'])
    night_date= fconn.send_eor_query('select timestamp_gps('+str(daylist[0]['obsid'])+')')
    night_date=str(night_date[0][0])[:19]
    query = 'SELECT ROWID FROM %s WHERE Julian_Day=%s'%(daytable_id,str(julian_day))
    response=fconn.send_fusion_query('GET',query,{})
    print response.status,response.reason
    response=json.loads(response.read())
    try:
        rowid=response['rows'][0][0]
        query = 'UPDATE %s\nSET Hours_EoR0=%s,Hours_EoR1=%s,Hours_EoR2=%s,Hours_Pawsey=%s,Hours_MRO=%s,Hours_MIT=%s,Hours_UVFITS=%s,Night_Date=\'%s\',Band=\'%s\'\nWHERE ROWID=\'%s\''%(daytable_id,str(hours_eor0),str(hours_eor1),str(hours_eor2),str(hours_pawsey),str(hours_mro),str(hours_mit),str(hours_uvfits),str(night_date),str(band),rowid)
        print query
        response=fconn.send_fusion_query('POST',query,{'Content-Length':0})
        print response.status,response.reason
    except KeyError:
        query = 'INSERT INTO %s (Julian_Day,Night_Date,Hours_EoR0,Hours_EoR1,Hours_EoR2,Hours_Pawsey,Hours_MRO,Hours_MIT,Hours_UVFITS,Band) VALUES (%s,\'%s\',%s,%s,%s,%s,%s,%s,%s,\'%s\')'%(daytable_id,str(julian_day),str(night_date),str(hours_eor0),str(hours_eor1),str(hours_eor2),str(hours_pawsey),str(hours_mro),str(hours_mit),str(hours_uvfits),str(band))
        print query
        response=fconn.send_fusion_query('POST',query,{'Content-Length':0})
        print response.status,response.reason





if __name__=='__main__':
    if(not(os.path.isfile(fusionname))):
        fuser=FusionConnector()
        pickle.dump(fuser,open(fusionname,'wb'))
    else:
        fuser=pickle.load(open(fusionname,'rb'))
    update_table(fuser)
