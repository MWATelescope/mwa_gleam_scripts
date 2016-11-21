
"""
GLEAM VO client / API

Dependency: pip install -U astropy

Usage example
====
import gleam_client
gleam_client.vo_get(50.67, -37.02, 1.0, freq=['072-080', '080-088'],
                    download_dir='/tmp')
====

Author: chen.wu@icrar.org
"""
import os, warnings
from urllib2 import urlopen, quote
from astropy.io.votable import parse_single_table

PROJ_OPTS = ['ZEA', 'ZEA_regrid', 'SIN']

class GleamClientException(Exception):
    pass

def download_file(url, ra, dec, freq, download_dir):
    """

    """
    u = urlopen(url, timeout=200)
    if (u.headers['content-type'] == 'image/fits'):
        # we know for sure this is a fits image file
        filename = "{0}_{1}_{2}.fits".format(ra, dec, freq)
    else:
        filename = "error_{0}_{1}_{2}.html".format(ra, dec, freq)

    block_sz = u.fp.bufsize
    fulnm = download_dir + "/" + filename
    with open(fulnm, 'wb') as f:
        while True:
            buff = u.read(block_sz)
            if not buff:
                break

            f.write(buff)
        print "File '{0}' downloaded to '{1}'".format(fulnm, download_dir)

def vo_get(ra, dec, ang_size, proj_opt='ZEA',
                   download_dir=None,
                   vo_host='mwa-web.icrar.org',
                   freq=[]):
    """
    proj_opt:   string, possible values:
                'ZEA'   (default)
                'ZEA_regrid'
                'SIN'
    freq:       A list of frequencies, e.g. ['223-231' '216-223']
                An empty list means ALL
    """
    if (download_dir and (not os.path.exists(download_dir))):
        raise GleamClientException("Invalid download dir: {0}"\
              .format(download_dir))

    if (not proj_opt in PROJ_OPTS):
        raise GleamClientException("Invalid projection: '{0}'."\
              " Should be one of {1}"\
              .format(proj_opt, PROJ_OPTS))

    url = "http://{0}/gleam_postage/q/siap.xml?FORMAT=ALL&VERB=2"\
          "&NTERSECT=OVERLAPS&".format(vo_host)
    pos_p = 'POS=%s' % quote('{0},{1}'.format(ra, dec))
    proj_opt_p = 'proj_opt=%s' % proj_opt
    size_p = 'SIZE=%f' % (float(ang_size))
    url += '&'.join([pos_p, proj_opt_p, size_p])
    #print url
    u = urlopen(url, timeout=200)
    warnings.simplefilter("ignore")
    tbl = parse_single_table(u.fp).array
    warnings.simplefilter("default")
    ignore_freq = len(freq) == 0
    c = 0
    for row in tbl:
        r_freq = row[0]
        r_url = row[1]
        if (ignore_freq or r_freq in freq):
            if (download_dir):
                download_file(r_url, ra, dec, r_freq, download_dir)
            else:
                print(r_freq, r_url)
            c += 1
    if (c == 0):
        warnings.warn("Invalid Freq {0}".format(freq))


def usage_examples():
    """
    Three examples to cutout Fornax A

    """
    ra = 50.67
    dec = -37.20
    ang_size = 1.0
    freq_low = ['072-080', '080-088']
    projection = 'SIN'
    dl_dir = '/tmp'

    # example 1 - just to see what is going to be downloaded (low frequencies)
    vo_get(ra, dec, ang_size, freq=freq_low)

    # example 2 - now really get them
    vo_get(ra, dec, ang_size, freq=freq_low, download_dir=dl_dir)

    # example 3 - download all frequencies (Not specifying freq means ALL freqs)
    vo_get(ra, dec, ang_size, download_dir=dl_dir)
