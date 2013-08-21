from add_obs_data import *
import os,pickle
import argparse

if __name__=='__main__':
    if(not(os.path.isfile(fusionname))):
        fuser=FusionConnector()
        pickle.dump(fuser,open(fusionname,'wb'))
    else:
        fuser=pickle.load(open(fusionname,'rb'))
    parser = argparse.ArgumentParser(description='Check if data is at MIT')
    parser.add_argument('obsid',metavar='obs_number',type=int)
    args=parser.parse_args()
    print fuser.check_mit(args.obsid)
    
    
