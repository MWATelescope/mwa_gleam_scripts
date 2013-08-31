from add_obs_data import *
import os,pickle
import argparse

if __name__=='__main__':
    if(not(os.path.isfile(fusionname))):
        fuser=FusionConnector()
        pickle.dump(fuser,open(fusionname,'wb'))
    else:
        fuser=pickle.load(open(fusionname,'rb'))
    parser = argparse.ArgumentParser(description='Find uvfits location')
    parser.add_argument('obsid',metavar='obs_number',type=int)
    args=parser.parse_args()
    print fuser.read_uvfits_loc(args.obsid)
    
    
