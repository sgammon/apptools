# -*- coding: utf-8 -*-

'''

    apptools2: model adapter for redis
    -------------------------------------------------
    |                                               |
    |   `apptools.model.adapter.redis`              |
    |                                               |
    |   allows apptools models to be efficiently    |
    |   stored in and retrieved from redis.         |
    |                                               |
    -------------------------------------------------
    |   authors:                                    |
    |       -- sam gammon (sam@momentum.io)         |
    -------------------------------------------------
    |   changelog:                                  |
    |       -- apr 1, 2013: initial draft           |
    -------------------------------------------------

'''

# stdlib
import json
import base64
import config

# 3rd party
import webapp2

# adapter API
from .abstract import ModelAdapter

# apptools util
from apptools.util import json
from apptools.util import debug
from apptools.util import decorators
from apptools.util import datastructures

# resolve msgpack
try:
    import msgpack
except ImportError as e:
    _MSGPACK = False

# resolve redis
try:
    ## force absolute import to avoid infinite recursion
    redis = __import__('redis', locals(), globals(), [], 0)
except ImportError as e:
    _REDIS = False
else:
    _REDIS = True

# resolve gevent
try:
    import gevent
except ImportError as e:
    _GEVENT = False
else:
    _GEVENT = True
    if _REDIS:
        ## with Redis AND gevent, patch the connection socket
        redis.connection.socket = gevent.socket


## Globals / Constants
_default_profile = None  # holds the default redis instance mapping
_profiles_by_model = {}  # holds specific model => redis instance mappings, if any


## RedisAdapter
# Adapt apptools models to Redis.
class RedisAdapter(ModelAdapter):

    ''' Adapt model classes to Redis. '''

    # key encoding
    adapter = None
    connection_spec = None
    _key_encoder = base64.b64encode
    _config_path = 'apptools.model.adapters.redis.Redis'

    # magic string identifiers
    _id_prefix = '__id__'
    _kind_prefix = '__kind__'

    # data compression / encoding
    _data_encoder = json.dumps
    _data_compressor = None

    @decorators.classproperty
    def config(cls):

        ''' Cached config shortcut. '''

        return config.config.get(cls._config_path, {'debug': True})

    @webapp2.cached_property
    def logging(self):

        ''' Named logging pipe. '''

        psplit = self._config_path.split('.')
        return debug.AppToolsLogger(path='.'.join(psplit[0:-1]), name=psplit[-1])._setcondition(self.config.get('debug', True))

    @webapp2.cached_property
    def codec(self):

        ''' Load and return the appropriate serialization codec. '''

        ## Use msgpack if available, fall back to JSON
        if _MSGPACK:
            return msgpack.pack
        return json

    @classmethod
    def is_supported(cls):

        ''' Check whether this adapter is supported in the current environment. '''

        return _REDIS

    @classmethod
    def acquire(cls, name, bases, properties):

        ''' Perform first initialization. '''

        global _default_profile
        global _profiles_by_model

        ## Resolve default
        servers = cls.config.get('servers', False)

        if not _default_profile:

            ## Resolve Redis config
            if not servers:
                return None  # no servers to connect to (on noez)

            for name, config in servers.items():
                if name == 'default' or config.get('default', False) == True:
                    _default_profile = name, config
                elif not _default_profile:
                    _default_profile = name, config

        # Resolve specific adapter, if listed explicitly
        if '__redis__' in properties and isinstance(properties.get('__redis__'), basestring):
            if properties['__redis__'] not in servers:
                raise ValueError("Model \"%s\" mapped to non-existent Redis profile \"%s\"." % (name, properties['__redis__']))
            else:
                _profiles_by_model['index'].add(name)
                _profiles_by_model['map'][name] = servers.get(properties['__redis__'], _default_profile)

        return super(RedisAdapter, cls).acquire(name, bases, properties)

    def channel(self, kind):

        ''' Retrieve a write channel to Redis. '''

        if not isinstance(model, basestring):
            kind = kind.kind()
        if kind in _profiles_by_model['index']:
            return self.adapter.StrictRedis(**_profiles_by_model['map'].get(kind))
        return self.adapter.StrictRedis(**_default_profile)

    @classmethod
    def get(cls, key):

        ''' Retrieve an entity by Key from Redis. '''

        import pdb; pdb.set_trace()
        return True

    @classmethod
    def put(cls, key, entity, model):

        ''' Persist an entity to storage in Redis. '''
        
        import pdb; pdb.set_trace()
        return True

    @classmethod
    def delete(cls, key):

        ''' Delete an entity by Key from Redis. '''

        import pdb; pdb.set_trace()
        return True

    @classmethod
    def encode_key(cls, key):

        ''' Encode a Key for storage in Redis. '''

        import pdb; pdb.set_trace()
        return True

    @classmethod
    def allocate_ids(cls, key_class, kind, count=1):

        ''' Allocate new Key IDs up to `count`. '''

        # generate kinded key to resolve ID pointer
        k = key_class(kind)
