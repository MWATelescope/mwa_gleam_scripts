#!/usr/bin/env python

import subprocess as sp
import psycopg2,os,glob
from datetime import datetime



if __name__=="__main__":
    #get the last command in mwa_setting
    eorconn = psycopg2.connect(database='mwa',host='eor-db.mit.edu',user='mwa',password='BowTie')
    cur = eorconn.cursor()
    cur.execute('select observation_number from obsc_mwa_setting where starttime < gpsnow() order by starttime desc limit 1')
    obsid=cur.fetchall()[0][0]
    #get current observation
    sp.call('/csr/mwa/python/mwa_git/mwatools_setup/bin/get_observation_info.py -g '+str(obsid)+' -i',shell=True)
    #get latest png
    #remove all images
    pngfile = sorted(glob.glob('/nfs/blank/h4215/aaronew/MWA_Tools/eorlive/*.png'),key=os.path.getmtime)
    pngfile = pngfile[len(pngfile)-1]
    print pngfile
    sp.call('mv '+pngfile+' current_beam.png',shell=True)
    f=open('/nfs/blank/h4215/aaronew/MWA_Tools/eorlive/current_beam.log','a')
    nowtime=datetime.now()
    f.write(nowtime.isoformat(' ')+' successfully executed')
    f.close()
    exit(0)
