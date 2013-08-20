import add_obs_data
import argparse

if __name__=='__main__':
    if(not(os.path.isfile(fusionname))):
        fuser=add_obs_data.FusionConnector()
        pickle.dump(fuser,open(fusername,'wb'))
    else:
        fuser=pickle.load(open(fusionname,'rb'))
    parser = argparse.ArgumentParser(description='Check if data is at MIT')
    parser.add_argument('obsid',metavar='obs_number',type=int,dest="obsid")
    (option,args)=parser.parse_args()
    return fuser.check_mit(args.obsid)
    
    
