"""
An example to show how Python VO client (pyvo) can be used to interact with GLEAM VO

Dependency: pip install -U astropy
            pip install -U wsgi_intercept

            pip install pyvo
            # if pip install pyvo failed, try:
            git clone https://github.com/pyvirtobs/pyvo.git
            cd pyvo
            python setup.py install

For any isssues, please email: chen.wu@icrar.org
"""
import base64, urlparse, os
from urllib2 import urlopen, Request

from wsgi_intercept import (
    urllib_intercept, add_wsgi_intercept, remove_wsgi_intercept
)

# which VO service to use
vo_name_dict={"cutout":"gleam_postage", "snapshot":"gleam"}

def run_cutout_example(access_url, regrid=False, download_dir=None):
    """
    PyVO examples are here
    """
    if (download_dir and (not os.path.exists(download_dir))):
        print "Invalid download dir: {0}".format(download_dir)
        return
    from pyvo.dal import sia
    svc = sia.SIAService(access_url) #start Simple Image Access service
    ra = 22 #313.07
    dec = -40 #-36.675
    pos = (ra, dec) # position
    size = 1.0 # angular size
    if (regrid):
        images = svc.search(pos, size, grid_opt="regrid")
    else:
        images = svc.search(pos, size)

    for img in images:
        # for each mached image, download or print its frequency and access url
        freq = img.get('freq')
        url = img.acref
        if (download_dir):
            download_file(url, ra, dec, freq, download_dir)
        else:
            print freq, url

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
        print "Downloading {0}".format(fulnm)
        while True:
            buff = u.read(block_sz)
            if not buff:
                break

            f.write(buff)

class GleamVoProxy():
    """
    This is NOT part of the example, just a helper class

    Since pyvo (http://pyvo.readthedocs.org/en/latest/pyvo/) does not support
    authorisation, we intercept each VO request and add credentials on the fly
    """
    def __init__(self, type='cutout', p_host='localhost', p_port=80):
        self._vo_host = 'mwa-web.icrar.org'
        self._p_host = p_host
        self._p_port = p_port
        self._vo_path = '/{0}/q/siap.xml?'.format(vo_name_dict[type])
        self._vo_url = "http://{0}{1}".format(self._vo_host, self._vo_path)
        self._access_url = "http://{0}:{2}{1}".format(self._p_host, self._vo_path, self._p_port)
        self._token = base64.encodestring('%s:%s' % ('Z2xlYW1lcg==\n'.decode('base64'), 'Qm93VGll\n'.decode('base64'))).replace('\n', '')

    @property
    def access_url(self):
        return self._access_url

    def _callback(self, environ, start_response):
        qs = environ['QUERY_STRING']
        dd = urlparse.parse_qs(qs)
        size_param = dd['SIZE'][0]
        val = 'SIZE={0}'.format(size_param)
        val1 = 'SIZE={0}'.format(size_param.split(',')[0])
        qs = qs.replace(val, val1)
        url = "http://{0}{1}?{2}".format(self._vo_host, environ['PATH_INFO'], qs)
        request = Request(url)
        request.add_header("Authorization", "Basic %s" % self._token)
        resp = urlopen(request)
        start_response('{0} {1}'.format(resp.code, resp.msg), [('content-type', 'application/x-votable+xml')])
        re = resp.read()
        return [re]

    def _make_callback(self):
        return self._callback

    def start(self):
        urllib_intercept.install_opener()
        add_wsgi_intercept(self._p_host, self._p_port, self._make_callback)

    def stop(self):
        remove_wsgi_intercept()

if __name__ == "__main__":
    """
    complete workflow
    """
    # start the gleam proxy
    gvp = GleamVoProxy()
    #gvp = GleamVoProxy(p_port=7799)
    gvp.start()

    # your VO code goes here
    run_cutout_example(gvp.access_url, download_dir='/tmp/gleamvo')

    # stop the gleam proxy
    gvp.stop()