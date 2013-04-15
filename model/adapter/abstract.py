# -*- coding: utf-8 -*-

'''

    apptools2: abstract model adapters
    -------------------------------------------------
    |                                               |
    |   `apptools.model.adapter.abstract`           |
    |                                               |
    |   specifies interface classes that plug-in    |
    |   to models to allow agnostic storage.        |
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
import abc


# Globals
_adapters = {}


## ModelAdapter
# Adapt apptools models to a storage backend.
class ModelAdapter(object):

    ''' Abstract base class for classes that adapt apptools models to a particular storage backend. '''

    registry = {}
    __metaclass__ = abc.ABCMeta

    ## == Internal Methods == ##
    def _get(self, key):

        ''' Internal method for retrieving an entity by Key. '''

        # immediately fail with no overriden `get`
        if not hasattr(self.__class__, 'get') and self.__class__ != ModelAdapter:  # pragma: no cover
            raise RuntimeError("ModelAdapter `%s` does not implement `get`, and thus cannot be used for reads." % self.__class__.__name__)
        else:
            # grab getter method
            getter = getattr(self.__class__, 'get')

        # flatten key into stringified repr
        joined, flattened = key.flatten(True)
        parent, kind, id = flattened

        # optionally allow adapter to encode key
        encoded = self.encode_key(joined, flattened)

        if not encoded:
            # otherwise, use regular base64 via `AbstractKey`
            encoded = key.urlsafe(joined)

        # pass off to delegated `get`
        try:
            entity = getter((encoded, flattened))
        except RuntimeError as e:  # pragma: no cover
            raise
        else:
            if entity is None:
                return  # not found

            # inflate key + model and return
            return self.registry[kind](key=self.registry[kind].__keyclass__(*(x for x in flattened if x is not None), _persisted=True), **entity)

    def _put(self, entity):

        ''' Internal method for persisting an Entity. '''

        # immediately fail with no overridden `put`
        if not hasattr(self.__class__, 'put') and self.__class__ != ModelAdapter:  # pragma: no cover
            raise RuntimeError("ModelAdapter `%s` does not implement `put`, and thus cannot be used for writes." % self.__class__.__name__)

        # resolve model class
        _model = self.registry.get(entity.kind())
        if not _model:  # pragma: no cover
            raise ValueError('Could not resolve model class "%s".' % model.kind())

        # validate entity
        for name, value in entity.to_dict(_all=True).items():
            _model.__dict__[name].valid(entity)  # will raise validation exceptions

        # resolve key
        if not entity.key:  # we have a zero-y key or a key class
            entity.key = _model.__keyclass__(entity.kind(), self.allocate_ids(entity.kind()))  # build an ID-based key

        # flatten key/entity
        joined, flattened = entity.key.flatten(True)

        # optionally allow adapter to encode key
        encoded = self.encode_key(joined, flattened)

        if not encoded:
            # otherwise, use regular base64 via `AbstractKey`
            encoded = entity.key.urlsafe(joined)

        # delegate
        saved_key = self.put((encoded, flattened), entity, _model)

        # set key as persisted
        return entity._set_persisted(True).key

    def _delete(self, key):

        ''' Internal method for deleting an entity by Key. '''

        joined, flattened = key.flatten(True)

        # optionally allow adapter to encode key
        encoded = self.encode_key(joined, flattened)

        if not encoded:
            # otherwise, use regular base64 via `AbstractKey`
            encoded = key.urlsafe(joined)

        return self.delete((encoded, flattened))

    @classmethod
    def _register(cls, model):

        ''' Internal method for registering a Model class with this adapter's registry. '''

        cls.registry[model.kind()] = model
        return model

    ## == Class Methods == ##
    @classmethod
    def acquire(cls):

        ''' Acquire a new/existing copy of this adapter. '''

        global _adapters

        # if we don't have one yet, spawn a singleton
        if cls.__name__ not in _adapters:
            _adapters[cls.__name__] = cls()
        return _adapters[cls.__name__]

    ## == Abstract Methods == ##
    @abc.abstractmethod
    def get(cls, key):  # pragma: no cover

        ''' Retrieve an entity by Key. Must accept a tuple in the format `(<joined Key repr>, <flattened key>)`. '''

        raise NotImplementedError()

    @abc.abstractmethod
    def put(cls, key, entity, model):  # pragma: no cover

        ''' Persist an Entity in storage. '''

        raise NotImplementedError()

    @abc.abstractmethod
    def delete(cls, key):  # pragma: no cover

        ''' Delete an entity by Key. '''

        raise NotImplementedError()

    @abc.abstractmethod
    def allocate_ids(cls, kind, count=0):  # pragma: no cover

        ''' Allocate new Key IDs for `kind` up to `count`. '''

        raise NotImplementedError()

    def encode_key(cls, joined, flattened):  # pragma: no cover

        ''' Encode a Key for storage. '''

        return None  # by default, yield to key b64 builtin encoding


## IndexedModelAdapter
# Adapt apptools models to a storage backend that supports indexing.
class IndexedModelAdapter(ModelAdapter):

    ''' Abstract base class for model adapters that support additional indexing APIs. '''

    @abc.abstractmethod
    def generate_indexes(cls, properties):  # pragma: no cover

        ''' Generate index entries from a set of indexed properties. '''

        raise NotImplemented()

    @abc.abstractmethod
    def write_indexes(cls, indexes):  # pragma: no cover

        ''' Write a batch of index updates generated earlier via the method above. '''

        raise NotImplemented()

    @abc.abstractmethod
    def execute_query(cls, spec):  # pragma: no cover

        ''' Execute a query across one (or multiple) indexed properties. '''

        raise NotImplemented()
