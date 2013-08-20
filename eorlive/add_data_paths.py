from add_obs_data import *
import os,pickle
import argparse

def add_paths(fconnector,obsid,uvpath,mspath):
    print obsid
    print uvpath
    print mspath
    rowid = fconnector.send_fusion_query('POST','SELECT ROWID FROM %s WHERE ObsID=%s'%(obstable_id,obsid),{'Content-Length':0})
    rowid=json.loads(rowid.read())
    rowid=rowid['rows'][0][0]
    query = 'UPDATE %s\nSET MS_Files=\'%s\', UVFITS_Files=\'%s\'\nWHERE ROWID=\'%s\''%(obstable_id,mspath,uvpath,str(rowid))
    response=fconnector.send_fusion_query('POST',query,{'Content-Length':0})
    print response.status,response.reason
    

if __name__=='__main__':
    if(not(os.path.isfile(fusionname))):
        fuser=FusionConnector()
        pickle.dump(fuser,open(fusionname,'wb'))
    else:
        fuser=pickle.load(open(fusionname,'rb'))
    parser = argparse.ArgumentParser(description='Check if data is at MIT')
    parser.add_argument('obsid',metavar='obs_number',type=int)
    parser.add_argument('-u','--uvfits',metavar='uvfits path',type=str,default='')
    parser.add_argument('-m','--ms',metavar='ms path',type=str,default='')
    args=parser.parse_args()
    
    add_paths(fuser,args.obsid,args.uvfits,args.ms)
    
    
