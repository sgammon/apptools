## Base Imports
import redis
import base64

## Model Imports
from apptools.util import json
from apptools.services import KeyMessage
from apptools.model.adapter import StorageAdapter
from apptools.model.adapter import ThinKeyAdapter
from apptools.model.adapter import ThinModelAdapter

## Gevent Compatibility
try:
    import geventredis as redis
    _GEVENT_MODE = True

except ImportError, e:
    import redis
    _GEVENT_MODE = False


## RedisKeyAdapter - adapts model keys to redis
class RedisKeyAdapter(ThinKeyAdapter):

    ''' Provides models with keys for use in Redis. '''

    ## == AppTools Model Hooks == ##
    @classmethod
    def __inflate__(cls, raw):

        ''' Inflate a raw structure from Redis into a key. '''

        # decode key
        chunks = []
        for chunk in base64.b64decode(raw).split(':'):
            chunks.append(base64.b64decode(chunk))

        chunks = tuple(chunks)

        # split key
        if len(chunks) == 3:
            ns, kind, id = chunks

        elif len(chunks) == 2:
            kind, id = chunks
            ns = None

        else:
            raise ValueError("Could not decode raw key '%s' into RedisKey." % raw)

        # inflate into an object
        return cls(namespace=ns, kind=kind, id=id, adapter=Redis, raw=raw)

    def __message__(self):

        ''' Convert this model into a structure suitable for transmission. '''

        id_prop = 'name'
        if isinstance(self.__id__, int):
            id_prop = 'id'

        # construct and return keymessage
        return KeyMessage(**{
            'encoded': self.__value__,
            'namespace': self.__namespace__,
            'kind': self.__kind__,
            id_prop: self.__id__
        })

    def __encode__(self):

        ''' Encode this key as a base64 string. '''

        if self.__value__:
            return self.__value__

        if not self.__id__:
            raise ValueError("Cannot URLsafe an incomplete key.")

    ## == Datastore Methods == ##
    def get(self):

        ''' Retrieve an entity from Redis by its key. '''

        return self.__adapter__.get(self)

    def delete(self):

        ''' Delete an entity in Redis by its key. '''

        return self.__adapter__.get(self)

    ## == Internal Key Methods == ##
    def id(self):

        ''' Retrieve this key's string/integer ID. '''

        return self.__id__

    def kind(self):

        ''' Retrieve this key's kind name. '''

        return self.__kind__

    def parent(self):

        ''' Retrieve this key's parent key. '''

        return None

    def pairs(self):

        ''' Retrieve this key's pairs. '''

        # we don't have inheritance
        return (self.__kind__, self.__id__)

    def app(self):

        ''' Retrieve the app that created this key. '''

        return self.__app__

    def urlsafe(self):

        ''' Generate a string representation of this key, suitable for use in a URL. '''

        if not self.__id__:
            raise ValueError("Cannot urlsafe incomplete key.")

        return self.__encode__()

    def flat(self):

        ''' Flatten this key. '''

        if not self.__id__:
            raise ValueError("Cannot flatten incomplete key.")

        return [i for i in filter(lambda x: x is not None, [
            self.__namespace__,
            self.__kind__,
            self.__id__
        ])]


## RedisModelAdapter - class that adapts thinmodels for storage in Redis
class RedisModelAdapter(ThinModelAdapter):

    ''' Adapts ThinModels to use Redis for storage. '''


    ## == AppTools Model Hooks == ##
    @classmethod
    def __inflate__(cls, key, struct):

        ''' Inflate a raw Redis structure into a model. '''

        properties = {}

        if isinstance(struct, list) and isinstance(struct[0], basestring):
            key = None
            for i in struct:
                if key:
                    properties[key] = i
                    key = None
                else:
                    key = i

        elif isinstance(struct, list) and isinstance(struct[0], tuple):
            properties = dict(struct)

        elif isinstance(struct, dict):
            properties = struct

        pmap = dict([(n, t) for (n, t, o) in cls.__pmap__[:]])

        filtered = {}
        for k in properties:
            if k in cls.__lookup__:

                try:
                    if pmap[k] in frozenset([basestring, str, unicode]):
                        filtered[k] = properties[k]

                    elif pmap[k] is int:
                        filtered[k] = int(properties[k])

                    elif pmap[k] is float:
                        filtered[k] = float(properties[k])

                    elif pmap[k] is bool:
                        filtered[k] = bool(properties[k])

                    elif properties[k] == _NONE_SENTINEL:
                        filtered[k] = None

                except ValueError, e:
                    raise ValueError("Error decoding property '%s' into object value. Encountered type mismatch with model prop type '%s'." % (k, pmap[k]))

        return cls(key=RedisKey.__inflate__(key), **filtered)

    def __message__(self):

        ''' Return a structured representation of this model, suitable for transmission. '''

        pass

    def __json__(self):

        ''' Return a JSON representation of this model. '''

        pass

    ## == Datastore Methods == ##
    def get(self):

        ''' Retrieve an entity from storage. '''

        pass

    def put(self):

        ''' Store/save an entity in storage. '''

        pass

    def delete(self):

        ''' Delete a model from storage. '''

        pass

    ## == Internal Model Methods == ##
    @property
    def key(self):

        ''' Retrieve this entity's key. '''

        pass

    def query(self):

        ''' Start a query from this ThinModel. '''

        pass


## Redis - central controller for redis interactions
class Redis(StorageAdapter):

    ''' Controller for adapting models to Redis. '''

    key = RedisKeyAdapter
    model = RedisModelAdapter

    def get(self, key, **opts): ''' Retrieve one or multiple entities by key. '''
    def put(self, entity, **opts): ''' Persist one or multiple entities. '''
    def delete(self, target, **opts): ''' Delete one or multiple entities. '''
    def query(self, kind=None, **opts): ''' Start building a query, optionally over a kind. '''
    def kinds(self, **opts): ''' Retrieve a list of active kinds in this storage backend. '''
