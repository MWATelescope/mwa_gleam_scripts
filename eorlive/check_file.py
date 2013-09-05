from add_obs_data import *
import os,pickle
import argparse

def check_ms(fconnector,obsid,boolmode):
    msfile = fconnector.send_fusion_query('POST','SELECT MS_Files FROM %s WHERE ObsID=%s'%(obstable_id,obsid),{'Content-Length':0})
    msfile = json.loads(msfile.read())
    msfile = msfile['rows'][0][0]
    if(boolmode):
        if(msfile):
            return 1
        else:
            return 0
    else:
        if(msfile):
            return msfile
        else:
            return ''

def check_uvfits(fconnector,obsid,boolmode):
    uvfile = fconnector.send_fusion_query('POST','SELECT UVFITS_Files FROM %s WHERE ObsID=%s'%(obstable_id,obsid),{'Content-Length':0})
    uvfile = json.loads(uvfile.read())
    uvfile = uvfile['rows'][0][0]
    if(boolmode):
        if(uvfile):
            return 1
        else:
            return 0
    else:
        if(uvfile):
            return uvfile
        else:
            return ''

    


if __name__=='__main__':
    if(not(os.path.isfile(fusionname))):
        fuser=FusionConnector()
        pickle.dump(fuser,open(fusionname,'wb'))
    else:
        fuser=pickle.load(open(fusionname,'rb'))
    parser = argparse.ArgumentParser(description='Check if uvfits or ms files have been made')
    parser.add_argument('obsid',metavar='obs_number',type=int)
    parser.add_argument('-u','--uvfits',metavar='uvfits path',dest='file_func',action='store_const',const=check_uvfits,help='get the file path of uvfits file')
    parser.add_argument('-m','--ms',metavar='ms path',dest='file_func',action='store_const',const=check_ms,help='get the file path of uvfits file')
    parser.add_argument('-b','--bool',metavar='boolean mode',dest='bool_mode',action='store_const',const=1,default=0)
    args=parser.parse_args()
    print(args.file_func(fuser,args.obsid,args.bool_mode))

    
    
    
