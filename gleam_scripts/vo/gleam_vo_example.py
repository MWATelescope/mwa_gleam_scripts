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
import base64, urlparse
from urllib2 import urlopen, Request

from wsgi_intercept import (
    urllib_intercept, add_wsgi_intercept, remove_wsgi_intercept
)

vo_name_dict={"cutout":"gleam_postage", "snapshot":"gleam"}

def run_cutout_example(access_url):
    """
    PyVO examples are here
    """
    from pyvo.dal import sia
    svc = sia.SIAService(access_url) #start Simple Image Access service
    pos = (22, -40) # position
    size = 2.0 # angular size
    images = svc.search(pos, size)
    for img in images:
        # for each mached image, print its frequency and access url
        print img.get('freq'), img.acref

class GleamVoProxy():
    """
    This is NOT part of the example, just a helper class

    Since pyvo (http://pyvo.readthedocs.org/en/latest/pyvo/) does not support
    authorisation, we intercept each VO request and add credentials on the fly
    """
    def __init__(self, type='cutout'):
        self._vo_host = 'mwa-web.icrar.org'
        self._p_host = 'localhost'
        self._vo_path = '/{0}/q/siap.xml?'.format(vo_name_dict[type])
        self._vo_url = "http://{0}{1}".format(self._vo_host, self._vo_path)
        self._access_url = "http://{0}{1}".format(self._p_host, self._vo_path)
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
        add_wsgi_intercept(self._p_host, 80, self._make_callback)

    def stop(self):
        remove_wsgi_intercept()

if __name__ == "__main__":
    """
    complete workflow
    """
    # start the gleam proxy
    gvp = GleamVoProxy()
    gvp.start()

    # your VO code goes here
    run_cutout_example(gvp.access_url)

    # stop the gleam proxy
    gvp.stop()