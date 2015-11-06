"""
Download GLEAM images from the postage stamp server using the template
code that Chen has written.

Paul Hancock
AUg - 2015
"""
import argparse
from gleam_vo_example import GleamVoProxy, download_file
import os
import pyvo
import sys

def get_cutout(access_url, ra, dec, size=1.0, freqs=[], regrid=False, download_dir=None, listf=False):
    """
    PyVO examples are here
    """
    if (download_dir and (not os.path.exists(download_dir))):
        print "Invalid download dir: {0}".format(download_dir)
        return
    from pyvo.dal import sia
    svc = sia.SIAService(access_url) #start Simple Image Access service
    pos = (ra, dec) # position
    if (regrid):
        images = svc.search(pos, size, grid_opt="regrid")
    else:
        images = svc.search(pos, size)
        
    if listf:
        print "Available freq ranges are:"
        for img in images:
            print img.get('freq')
        return
    for img in images:
        # for each mached image, download or print its frequency and access url
        freq = img.get('freq')
        # only process the frequencies of interest
        if not freq in freqs:
            continue
        print 'dl'
        url = img.acref
        if (download_dir):
            download_file(url, ra, dec, freq, download_dir)
        else:
            print freq, url

if __name__=="__main__":
    parser = argparse.ArgumentParser()

    group1=parser.add_argument_group('Downloading cutouts from the GLEAM VO server')
    # arguments
    group1.add_argument('-o', dest='outdir', action='store', help='output directory', default='.')
    group1.add_argument('-ra', dest='ra', action='store', metavar='RA', default=None, type=float,
                        help='RA of image center in degrees')
    group1.add_argument('-dec', dest='dec', action='store', metavar='DEC', default=None, type=float,
                        help='DEC of image center in degrees')
    group1.add_argument('-size', dest='size', action='store', metavar='SIZE', default=1.0, type=float,
                        help='Size of image to cut out in degrees, max is 5.')
    group1.add_argument('-freqs', dest='freqs', action='store', metavar='FREQ', type=str, default=['170-231'], nargs='*',
                        help='Download only cutout images of these frequencies. Default (170-231) is the deep image.')
    group1.add_argument('-lf', dest='listf', action='store_true', default=False,
                        help='List all the freqs that are available for this cutout region')

    results = parser.parse_args()

    if results.ra is None or results.dec is None:
        print "ERR: must specify both ra/dec"
        sys.exit(1)
    
    # start the gleam proxy
    gvp = GleamVoProxy()
    #gvp = GleamVoProxy(p_port=7799)
    gvp.start()

    # your VO code goes here
    get_cutout(gvp.access_url, results.ra, results.dec, results.size, results.freqs, 
               download_dir=results.outdir, listf =results.listf)
    #run_cutout_example(gvp.access_url, download_dir='/tmp/gleamvo')

    # stop the gleam proxy
    gvp.stop()
