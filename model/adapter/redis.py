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

# adapter API
from .abstract import ModelAdapter


## RedisAdapter
# Adapt apptools models to Redis.
class RedisAdapter(ModelAdapter):

    ''' Adapt model classes to Redis. '''

    # key encoding
    _key_encoder = base64.b64encode

    # data compression / encoding
    _data_encoder = json.dumps
    _data_compressor = None

    @classmethod
    def is_supported(cls):

        ''' Check whether this adapter is supported in the current environment. '''

        return True

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
    def allocate_ids(cls, kind, count=1):

        ''' Allocate new Key IDs up to `count`. '''

        pass
