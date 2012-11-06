# Base Imports
import config
import webapp2

# AppTools Utils
from apptools.util import json
from apptools.util import debug

# AppTools Model Adapters
from apptools.model.adapter import StorageAdapter
from apptools.model.adapter import ThinKeyAdapter
from apptools.model.adapter import ThinModelAdapter

## Constants
_CONFIG_PATH = 'apptools.model.adapters.memcache.Memcache'
logging = debug.AppToolsLogger(path='apptools.model.adapter', name='memcache')._setcondition(config.config.get(_CONFIG_PATH))


## Resolve Memcache Client
try:
    from google.appengine.api import memcache
    _MEMCACHE = True
    _GAE = True
except ImportError:
    try:
        import memcache
        _MEMCACHE = True
        _GAE = False
    except ImportError as e:
        logging.warning('Memcache is not supported in the current environment, but it was still loaded. Please remove or disable the memcache model adapter from config.')
        pass


## MemcacheKeyAdapter - adapts ThinModel keys to memcache
class MemcacheKeyAdapter(ThinKeyAdapter):

    ''' Adapts memcache keys to ThinModel. '''

    ## == AppTools Model Hooks == ##
    @classmethod
    def __inflate__(cls, raw):

        ''' Inflate a raw string key into a ThinKey. '''

        return cls()

    def __encode__(self):

        ''' Encode this key. Return a testing string for now. '''

        return '__TESTING__'


## MemcacheModelAdapter - adapts ThinModels to memcache-compliant interfaces
class MemcacheModelAdapter(ThinModelAdapter):

    ''' Adapts ThinModels to memcache. '''

    @classmethod
    def __inflate__(cls, key, struct):

        ''' Inflate to an NDB model from a raw structure. '''

        k = MemcacheKeyAdapter.__inflate__(key)
        return cls(key=k, **struct)

    def __json__(self):

        ''' Output a JSON-encoded representation of this model. '''

        return json.dumps(self.to_dict())

    def __message__(self):

        ''' Output a structured representation of this model, suitable for transmission. '''

        return self.to_message()


## Memcache - adapts apptools models to memcache-compliant storage engines
class Memcache(StorageAdapter):

    ''' Adapts the AppTools core model APIs to memcache-compliant storage engines. '''

    key = MemcacheKeyAdapter
    model = MemcacheModelAdapter

    ## == Internal Shortcuts == ##
    @webapp2.cached_property
    def config(self):

        ''' Named config pipe. '''

        return config.config.get(_CONFIG_PATH)

    @webapp2.cached_property
    def logging(self):

        ''' Named logging pipe. '''

        global logging
        return logging.extend(name='Memcache')._setcondition(self.config.get('debug', True))

    @webapp2.cached_property
    def client(self):

        ''' Return the current memcache client. '''

        if not _GAE:
            if len(self.config.get('servers')) > 0:
                return memcache.Client(
                    map(lambda x: ':'.join(x), [(block.get('host', '127.0.0.1'), block.get('port', 11211)) for block in self.config.get('servers').values()]),
                    debug=int(config.debug))
            else:
                raise RuntimeError("Cannot construct memcache client for empty server configuration.")
        else:
            return memcache.Client()


    ## == Datastore Methods == ##
    def get(self, key, **opts):

        ''' Retrieve one or multiple entities by key. '''

        self.logging.debug('Retrieving value from memcache at key "%s".' % key)
        return self.client.get(self.key.__inflate__(key).__encode__(), **opts)

    def put(self, entity, **opts):

        ''' Persist one or multiple entities. '''

        self.logging.debug('Persisting entity in memcache at key "%s".' % entity.key)
        return self.client.set(entity.key.__encode__(), entity.__json__(), **opts)

    def delete(self, target, **opts):

        ''' Delete one or multiple entities. '''

        self.logging.debug('Deleting entity in memcache at key "%s".' % target.key)
        return self.client.delete(target.key.__encode__(), **opts)

    def query(self, kind=None, **opts):

        ''' Start building a query, optionally over a kind. '''

        self.logging.error('Queries are not supported in memcache.')
        raise NotImplemented  # queries not supported in memcache

    def kinds(self, **opts):

        ''' Retrieve a list of active kinds in memcache. '''

        self.logging.info('Kind lists are not supported in memcache.')
        raise NotImplemented  # kindlists not supported in memcache
