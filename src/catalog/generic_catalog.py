"""
The PAPER catalog here is derived by experimental methods in either facets or 
healpix maps.
"""

import aipy as a, numpy as n, os,logging,vo.table as vot
import ephem, warnings,sys

logging.basicConfig(level=logging.CRITICAL)
log = logging.getLogger('generic_catalog')
warnings.simplefilter('ignore',Warning)
lastmod = "18 Feb 2011"
def pos2name(ra,dec):
    raname=''.join(str(ephem.hours(ra)).split(':')).split('.')[0]
    decname=''.join(str(ephem.degrees(dec)).split(':')).split('.')[0]
    if n.sign(dec)>0.: decname = '+'+decname
    return raname+decname


class RadioFixedBody(a.fit.RadioFixedBody):
    def __init__(self,*args,**kwargs):
        a.fit.RadioFixedBody.__init__(self, *args, **kwargs)
        if kwargs.has_key('e_S_nu'):self.e_S_nu = kwargs['e_S_nu']
        if kwargs.has_key('vo_record'): self.vo_record = kwargs['vo_record']

    
class GENERICCatalog(a.fit.SrcCatalog):
    def fromfile(self, filename):
        addsrcs = []
        data = n.genfromtxt(filename,names=True,dtype=None)
        altnames = {'S_nu':'jys','nu':'mfreq','Ra':'ra','Dec':'dec'}
        prms = {'jys':0,'Name':'','index':0,'mfreq':0.15,'e_S_nu':0,'ra':0,'dec':0}
        for rec in data:
            for prm in data.dtype.names:
                try:
                    if prms.has_key(prm): prms[prm]=rec[prm]
                    elif prms.has_key(altnames[prm]):
                        prms[altnames[prm]] = rec[prm]
                    else: 
                        log.error("column not recognized")
                except(KeyError):
                        log.warning("Skipping unknown parameter "+prm)
            addsrcs.append(RadioFixedBody(prms['ra'],prms['dec'],name=prms['Name'],
                jys=prms['jys'],index=prms['index'],mfreq=prms['mfreq'],e_S_nu=prms['e_S_nu']))
        self.add_srcs(addsrcs)
        
                    
#    def fromfile(self, filename):
#        f = open(filename)
#        addsrcs = []
#        for L in [L for L in f.readlines() if not L.startswith('#')]:
#            text = L.split('\t')
#            if len(text) <= 3: continue
##            try: int(text[0].strip()[0])
##            except(ValueError): continue
#            ra = text[1]
#            dec = text[2]
#            name = text[0].strip()
#            jys = float(text[3])
#            try: e_S_nu = float(text[4])
#            except(IndexError): e_S_nu = 0
#            addsrcs.append(RadioFixedBody(ra, dec, name=name,
#                jys=jys, index=0, mfreq=.150,e_S_nu=e_S_nu))
#        self.add_srcs(addsrcs)
    def fromvot(self,filename):
        log.info("\n"+"#"*50 + "\n This is generic_catalog.py last modified %s\n"%(lastmod,) + "#"*50)
        addsrcs = []
        votable = vot.parse_single_table(filename,pedantic=False)
        #try and find the frequency, if a single freq catalog
        default_nu = 0.15
        for prm in votable.params:
            if prm.ucd=="em.freq": 
                default_nu=prm.value
                if prm.unit=='MHz': default_nu /= 1e3
                if prm.unit=='kHz': default_nu /= 1e6
                log.info("Setting the default mfreq=%f"%default_nu)
        #find the names of the columns based on my desired ucds
        ucds = {"pos.eq.ra;meta.main":'Ra',
                "pos.eq.dec;meta.main":'Dec',
                "phot.flux.density":'S_nu_',
                "stat.error":'e_S_nu_',
                "meta.id;meta.main":'Name',
                "meta.record":'Seq',
                "spect.index":'n',
                "em.freq":'nu'}
        Jys = 1.0
        GHz = 1.0
        fluxname = None
        for field in votable.fields:
            log.info("loading field: %s ucd=%s"%(field.name,field.ucd,))
            if field.ucd is None: continue
            if field.ucd.endswith("meta.main"):
                ucds.update({field.ucd:field.name})
            else:
                ucds.update({field.ucd.split(';')[0]:field.name})
            if field.ucd.startswith('phot.flux.density'):
                if field.unit=='mJy': Jys=1.e-3
                log.info("1 Jy is %f times catalog flux"%(1./Jys,))
                if field.ucd == 'phot.flux.density;em.radio.100-200MHz':
                    fluxname = field.name
                elif fluxname is None:
                    fluxname = ucds['phot.flux.density']
                log.info("using field %s for primary flux"%(fluxname,))
            if field.ucd.startswith('em.freq'):
                if field.unit=='MHz': GHz=1e-3
                elif field.unit=='kHz': GHz=1e-6
        for rec in votable.array:
            ra = rec[ucds["pos.eq.ra;meta.main"]]*a.img.deg2rad
            dec = rec[ucds["pos.eq.dec;meta.main"]]*a.img.deg2rad
            try: name = rec[ucds["meta.id;meta.main"]]
            except(IndexError): name = pos2name(ra,dec)
            try: jys = rec[fluxname]*Jys
            except(IndexError): print fluxname,'not found in ',rec.dtype.names
            try: e_S_nu = rec[ucds["stat.error"]]
            except(IndexError): e_S_nu = 0
            try: index = rec[ucds["spect.index"]]
            except(IndexError):
                try: index = rec['index']
                except: index=-1
            try:nu = rec[ucds["em.freq"]]*GHz
            except(IndexError):nu = default_nu
            addsrcs.append(RadioFixedBody(ra, dec, name=name,
                jys=jys, index=index, mfreq=nu,e_S_nu=e_S_nu,vo_record=rec))            
        self.add_srcs(addsrcs)

#GENERICFILE = os.path.dirname(__file__) + os.sep + 'generic.txt'
_genericcat = {}

def get_srcs(srcs=None, cutoff=None,catalogs=None,loglevel=logging.ERROR):
    log.setLevel(loglevel)
    global _genericcat
    if catalogs is None: return []
    if type(catalogs) is list: catalog=catalogs[0]
    else: catalog = catalogs
    GENERICFILE = os.path.dirname(__file__) + os.sep+catalog+'.txt'
    GENERICVOT = os.path.dirname(__file__) + os.sep+catalog+'.vot'
    try: 
        open(GENERICVOT)
        GENERICFILE=GENERICVOT
        log.info("opening %s"%(GENERICFILE))
    except(IOError): 
        try: 
            open(catalog+'.vot')
            GENERICFILE=catalog+'.vot'
            log.info("opening %s"%(GENERICFILE))
        except(IOError): 
            try: 
                open(GENERICFILE)
                log.info("opening %s"%(GENERICFILE))
            except(IOError):
                try: 
                    open(catalog+'.txt')
                    GENERICFILE=catalog+'.txt'
                    log.info("opening %s"%(GENERICFILE))
                except(IOError):
                    log.warning("%s %s"%(GENERICFILE,"not found"))
                    return []
    if not _genericcat.has_key(GENERICFILE):
        log.info("reading file")
        _genericcat[GENERICFILE] = GENERICCatalog()
        if GENERICFILE.endswith('.txt'):
            _genericcat[GENERICFILE].fromfile(GENERICFILE)
        elif GENERICFILE.endswith('.vot'):
            _genericcat[GENERICFILE].fromvot(GENERICFILE)
        log.info("loaded %d sources from %s"%(len(_genericcat[GENERICFILE]),GENERICFILE))
    if srcs is None:
        if cutoff is None: srcs = _genericcat[GENERICFILE].keys()
        else:
            cut, fq = cutoff
            fq = n.array([fq])
            for s in _genericcat[GENERICFILE].keys(): _genericcat[GENERICFILE][s].update_jys(fq)
            srcs = [s for s in _genericcat[GENERICFILE].keys() if _genericcat[GENERICFILE][s].jys[0] > cut]

    srclist = []
    for s in srcs:
        try:
            try: srclist.append(_genericcat[GENERICFILE][s.src_name])
            except(AttributeError):
                srclist.append(_genericcat[GENERICFILE][s])
        except(KeyError): pass
    return srclist
