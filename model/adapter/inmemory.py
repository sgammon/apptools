# -*- coding: utf-8 -*-

'''

    apptools2: model adapter for thread memory
    -------------------------------------------------
    |                                               |   
    |   `apptools.model.adapter.inmemory`           |
    |                                               |
    |   allows apptools models to be stored in      |
    |   main RAM, as a testing tool.                |
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


## Globals
_init = False
_metadata = {}
_datastore = {}


## InMemoryAdapter
# Adapt apptools models to Python RAM.
class InMemoryAdapter(ModelAdapter):

    ''' Adapt model classes to RAM. '''

    # key encoding
    _key_encoder = base64.b64encode

    # data compression / encoding
    _data_encoder = json.dumps
    _data_compressor = None

    @classmethod
    def acquire(cls, name, bases, properties):

        ''' Perform first initialization. '''

        global _init
        global _metadata

        # perform first init, if it hasn't been done
        if not _init:
            _init, _metadata = True, {
                'ops': {  # holds count of performed operations
                    'get': 0,  # track # of entity get() operations
                    'put': 0,  # track # of entity put() operations
                    'delete': 0  # track # of entity delete() operations
                },
                'kinds': {},  # holds current count and ID increment pointer for each kind
                'lookup': set(tuple()),  # holds all stringified keys for quick comparison/lookup
                'global': {  # holds global metadata, like entity count across kind classes
                    'entity_count': 0  # holds global count of all entities
                },
            }

        # pass up the chain to create a singleton
        return super(InMemoryAdapter, cls).acquire(name, bases, properties)

    @classmethod
    def is_supported(cls):

        ''' Check whether this adapter is supported in the current environment. '''

        # always supported: used in dev/debug, RAM is always there
        return True

    @classmethod
    def get(cls, key):

        ''' Retrieve an entity by Key from Python RAM. '''

        global _metadata

        # key format: tuple(<str encoded key>, <tuple flattened key>)
        encoded, flattened = key
        parent, kind, id = flattened

        # pull from in-memory backend
        entity = _datastore.get(encoded)
        if entity is None: return  # not found

        _metadata['ops']['get'] = _metadata['ops']['get'] + 1

        # construct + inflate entity
        return entity

    @classmethod
    def put(cls, key, entity, model):

        ''' Persist an entity to storage in Python RAM. '''
        
        global _metadata
        global _datastore

        # encode key and flatten
        encoded, flattened = key

        # perform validation
        with entity:

            # update metadata
            if encoded not in _metadata['lookup']:
                
                _metadata['lookup'].add(encoded)  # add to lookup

                if entity.key.kind not in _metadata['kinds']:  # pragma: no cover
                    _metadata['kinds'][entity.key.kind] = {
                        'id_pointer': 0,  # keep current key ID pointer
                        'entity_count': 0  # keep count of seen entities for each kind
                    }

                # update count
                _metadata['lookup'].add(encoded)  # add to encoded key lookup
                _metadata['ops']['put'] = _metadata['ops'].get('put', 0) + 1
                _metadata['global']['entity_count'] = _metadata['global'].get('entity_count', 0) + 1
                _metadata['kinds'][entity.key.kind]['entity_count'] = _metadata['kinds'][entity.key.kind].get('entity_count', 0) + 1

            # save to datastore
            _datastore[encoded] = entity.to_dict()

        return entity.key

    @classmethod
    def delete(cls, key):

        ''' Delete an entity by Key from memory. '''

        global _metadata
        global _datastore

        # extract key
        encoded, flattened = key
        parent, kind, id = flattened

        if encoded in _metadata['lookup']:
            try:
                del _datastore[encoded]  # delete from datastore

            except KeyError, e:  # pragma: no cover
                _metadata['lookup'].remove(encoded)
                return False  # untrimmed key

            else:
                # update meta
                _metadata['lookup'].remove(encoded)
                _metadata['ops']['delete'] = _metadata['ops'].get('delete', 0) + 1
                _metadata['global']['entity_count'] = _metadata['global'].get('entity_count', 1) - 1
                _metadata['kinds'][kind]['entity_count'] = _metadata['kinds'][kind].get('entity_count', 1) - 1

            return True
        return False

    @classmethod
    def allocate_ids(cls, key_class, kind, count=1):

        ''' Allocate new Key IDs up to `count`. '''

        global _metadata

        # resolve kind meta and increment pointer
        kind_blob = _metadata['kinds'].get(kind, {})
        current = kind_blob.get('id_pointer', 0)
        pointer = kind_blob['id_pointer'] = (current + count)

        # update kind blob
        _metadata['kinds'][kind] = kind_blob

        # return IDs
        if count > 1:
            def _generate_id_range():
                for x in xrange(current, pointer):
                    yield x
                raise StopIteration()
            return _generate_id_range
        return pointer
