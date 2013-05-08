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
import zlib
import base64
import datetime

# apptools utils
from apptools.util import json
from apptools.util import debug
from apptools.util import decorators
from apptools.util import datastructures

# appconfig
try:
    import config
except ImportError as e:  # pragma: no cover
    _APPCONFIG = False
else:
    _APPCONFIG = True


# Globals
_adapters = {}
_adapters_by_model = {}
_encoder = base64.b64encode  # encoder for key names and special strings, if enabled
_compressor = zlib.compress  # compressor for data values, if enabled

# Computed Classes
CompoundKey = None
CompoundModel = None


## ModelAdapter
# Adapt apptools models to a storage backend.
class ModelAdapter(object):

    ''' Abstract base class for classes that adapt apptools models to a particular storage backend. '''

    registry = {}
    __metaclass__ = abc.ABCMeta

    _config_path = 'apptools.model'

    @decorators.classproperty
    def config(cls):  # pragma: no cover

        ''' Cached config shortcut. '''

        if _APPCONFIG:
            return config.config.get(cls._config_path, {'debug': True})
        return {'debug': True}  # default to `debug`: True with no available appconfig

    @decorators.classproperty
    def logging(cls):

        ''' Named logging pipe. '''

        psplit = cls._config_path.split('.')
        return debug.AppToolsLogger(path='.'.join(psplit[0:-1]), name=psplit[-1])._setcondition(cls.config.get('debug', True))

    @decorators.classproperty
    def serializer(cls):

        ''' Load and return the appropriate serialization codec. '''

        # default to JSON
        return json

    @decorators.classproperty
    def encoder(cls):  # pragma: no cover

        ''' Encode a stringified blob for storage. '''

        # use local encoder
        return _encoder

    @decorators.classproperty
    def compressor(cls):  # pragma: no cover

        ''' Load and return the appropriate compression codec. '''

        return _compressor

    ## == Internal Methods == ##
    def _get(self, key):

        ''' Internal method for retrieving an entity by Key. '''

        if self.config.get('debug', False):  # pragma: no cover
            self.logging.info("Retrieving entity with Key: \"%s\"." % key)

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
            return self.registry[kind](key=self.registry[kind].__keyclass__(*(x for x in flattened if x is not None), _persisted=True), _persisted=True, **entity)

    def _put(self, entity):

        ''' Internal method for persisting an Entity. '''

        if self.config.get('debug', False):  # pragma: no cover
            self.logging.info("Saving entity: \"%s\"." % entity)

        # resolve model class
        _model = self.registry.get(entity.kind())
        if not _model: raise ValueError('Could not resolve model class "%s".' % model.kind())

        with entity:  # enter explicit mode

            # validate entity, will raise validation exceptions
            for name, value in entity.to_dict(_all=True).items():
                _model.__dict__[name].valid(entity)

            # resolve key if we have a zero-y key or key class
            if not entity.key or entity.key is None:
                entity._set_key(_model.__keyclass__(entity.kind(), self.allocate_ids(_model.__keyclass__, entity.kind())))  # build an ID-based key

            # flatten key/entity
            joined, flattened = entity.key.flatten(True)

        # delegate
        return self.put((self.encode_key(joined, flattened) or entity.key.urlsafe(joined), flattened), entity._set_persisted(True), _model)

    def _delete(self, key):

        ''' Internal method for deleting an entity by Key. '''

        if self.config.get('debug', False):  # pragma: no cover
            self.logging.info("Deleting Key: \"%s\"." % key)

        joined, flattened = key.flatten(True)
        return self.delete((self.encode_key(joined, flattened) or key.urlsafe(joined), flattened))

    @classmethod
    def _register(cls, model):

        ''' Internal method for registering a Model class with this adapter's registry. '''

        if cls.config.get('debug', False):
            cls.logging.info("Registered Model class: \"%s\"." % model)

        cls.registry[model.kind()] = model
        return model

    ## == Class Methods == ##
    @classmethod
    def acquire(cls, name, bases, properties):

        ''' Acquire a new/existing copy of this adapter. '''

        global _adapters
        global _adapters_by_model

        # if we don't have one yet, spawn a singleton
        if cls.__name__ not in _adapters:
            _adapters[cls.__name__] = cls()
        _adapters_by_model[name] = _adapters[cls.__name__]
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
    def allocate_ids(cls, key_class, kind, count=0):  # pragma: no cover

        ''' Allocate new Key IDs for `kind` up to `count`. '''

        raise NotImplementedError()

    @classmethod
    def encode_key(cls, key, joined=None, flattened=None):  # pragma: no cover

        ''' Encode a Key for storage. '''

        return False  # by default, yield to key b64 builtin encoding


## IndexedModelAdapter
# Adapt apptools models to a storage backend that supports indexing.
class IndexedModelAdapter(ModelAdapter):

    ''' Abstract base class for model adapters that support additional indexing APIs. '''

    # magic prefixes
    _key_prefix = '__key__'
    _kind_prefix = '__kind__'
    _group_prefix = '__group__'
    _index_prefix = '__index__'
    _reverse_prefix = '__reverse__'

    ## Indexer
    # Holds routines and data type tools for indexing apptools models in Redis.
    class Indexer(object):

        ''' Holds methods for indexing and handling index data types. '''

        _magic = {
            'key': 0x1,  # magic ID for `model.Key` references
            'date': 0x2,  # magic ID for `datetime.date` instances
            'time': 0x3,  # magic ID for `datetime.time` instances
            'datetime': 0x4  # magic ID for `datetime.datetime` instances
        }

        @classmethod
        def convert_key(cls, key):

            ''' Convert a `Key` to an indexable value. '''

            # flatten and return key structure with magic
            joined, flattened = key.flatten(True)
            return (cls._magic['key'], map(lambda x: x is not None, flatten))

        @classmethod
        def convert_date(cls, date):

            ''' Convert a `date` to an indexable value. '''

            # convert to ISO format, return date with magic
            return (cls._magic['date'], date.isoformat())

        @classmethod
        def convert_time(cls, _time):

            ''' Convert a `time` to an indexable value. '''

            # convert to ISO format, return time with magic
            return (cls._magic['time'], date.isoformat())

        @classmethod
        def convert_datetime(cls, _datetime):

            ''' Convert a `datetime` to an indexable value. '''

            # convert to integer, return datetime with magic
            return (cls._magic['datetime'], int(time.mktime(_datetime.timetuple())))

    @decorators.classproperty
    def _index_basetypes(self):

        ''' Map basetypes to indexer routines. '''

        return {

            int: self.serializer.dumps,
            bool: self.serializer.dumps,
            float: self.serializer.dumps,
            basestring: self.serializer.dumps,
            datetime.date: self.Indexer.convert_date,
            datetime.time: self.Indexer.convert_time,
            datetime.datetime: self.Indexer.convert_datetime

        }

    def _put(self, entity):

        ''' Hook to trigger index writes for a given entity. '''

        # small optimization - with a determined key, we can parrellelize index writes (assuming async is supported in the underlying driver)
        if entity.key:

            # proxy to `generate_indexes` and write indexes
            indexes = self.write_indexes(self.generate_indexes(entity.key, self._pluck_indexed(entity)))

            # delegate up the chain for entity write
            return super(IndexedModelAdapter, self)._put(entity)

        # delegate write up the chain
        written_key = super(IndexedModelAdapter, self)._put(entity)

        # proxy to `generate_indexes` and write
        indexes = self.write_indexes(self.generate_indexes(written_key, self._pluck_indexed(entity)))

        return written_key

    def _delete(self, key):

        ''' Hook to trigger index cleanup for a given key. '''

        # generate meta indexes only, then clean
        indexes = self.clean_indexes(self.generate_indexes(key))

        # delegate delete up the chain
        return super(IndexedModelAdapter, self)._delete(key)

    def _pluck_indexed(self, entity):

        ''' Zip and pluck only properties that should be indexed. '''

        _map = {}

        # grab only properties enabled for indexing
        for k, v in filter(lambda x: entity.__class__.__dict__[x[0]]._indexed, entity.to_dict().items()):
            _map[k] = (entity.__class__.__dict__[k], v)  # attach property name, property class, value

        return _map

    @classmethod
    def generate_indexes(cls, key, properties=None):

        ''' Generate a set of indexes that should be written to, with associated values. '''

        # provision vars, generate meta indexes
        encoded_key = cls.encode_key(key) or key.urlsafe()

        _property_indexes, _meta_indexes = [], [
            (cls._key_prefix,),  # add key to universal key index
            (cls._kind_prefix, key.kind)  # map kind to encoded key
        ]

        # consider ancestry
        if not key.parent:

            # generate group indexes in the case of a nonvoid parent
            _meta_indexes.append((cls._group_prefix,))

        else:

            # append keyparent-based group prefix
            root_key = [i for i in key.ancestry][0]

            # encode root key
            encoded_root_key = cls.encode_key(root_key) or root_key.urlsafe()

            _meta_indexes.append((cls._group_prefix, root_key))

        # add property index entries
        if properties:

            # we're applying writes
            for k, v in properties.items():

                # extract property class and value
                prop, value = v

                # consider repeated properties
                if not prop._repeated:
                    value = [value]

                # iterate through property values
                for v in value:
                    _property_indexes.append((cls._index_basetypes.get(prop._basetype, basestring), (cls._index_prefix, key.kind, k, v)))

                continue

        else:
            if cls.config.get('debug', False):  # pragma: no cover
                cls.logging.info("Generated indexes for clean: \"%s\" under key \"%s\"." % (_meta_indexes, encoded_key))

            # we're cleaning indexes
            return encoded_key, _meta_indexes

        if cls.config.get('debug', False):  # pragma: no cover
            cls.logging.info("Generated indexes for write: META(\"%s\"), VALUE(\"%s\") under key \"%s\"." % (_meta_indexes, _property_indexes, encoded_key))

        # we're writing indexes
        return encoded_key, _meta_indexes, _property_indexes

    @abc.abstractmethod
    def write_indexes(cls, writes):  # pragma: no cover

        ''' Write a batch of index updates generated earlier via the method above. '''

        raise NotImplementedError()

    @abc.abstractmethod
    def clean_indexes(cls, key):  # pragma: no cover

        ''' Clean indexes and index entries matching a key. '''

        raise NotImplementedError()

    @abc.abstractmethod
    def execute_query(cls, spec):  # pragma: no cover

        ''' Execute a query across one (or multiple) indexed properties. '''

        raise NotImplementedError()


## Mixin
# Metaclass for registering mixins and applying them later.
class Mixin(object):

    ''' Abstract parent for detecting and registering `Mixin` classes. '''

    __slots__ = tuple()

    class __metaclass__(type):

        ''' Local `Mixin` metaclass for registering encountered `Mixin`(s). '''

        ## == Mixin Registry == ##
        _compound = {}
        _mixin_lookup = set()
        _key_mixin_registry = {}
        _model_mixin_registry = {}

        def __new__(cls, name, bases, properties):

            ''' Factory a new registered `Mixin`. '''

            # apply local metaclass to factoried concrete children
            klass = super(cls, cls).__new__(cls, name, bases, properties)

            # register mixin if it's not a concrete parent and is unregistered
            if name not in frozenset(('Mixin', 'KeyMixin', 'ModelMixin', 'CompoundKey', 'CompoundModel')) and name not in cls._mixin_lookup:
                if KeyMixin not in bases and ModelMixin not in bases:
                    ## we can only directly extend `Mixin` from `KeyMixin` and `ModelMixin`
                    raise RuntimeError("Cannot directly extend `Mixin` - you must extend `KeyMixin` or `ModelMixin`.")
                elif len(bases) > 1:
                    for base in bases:
                        if base not in frozenset((KeyMixin, ModelMixin)):
                            ## mixins are only allowed to _directly_ extend `KeyMixin` or `ModelMixin` - no midway classes.
                            raise RuntimeError("Cannot inject classes for inheritance in between `KeyMixin` or `ModelMixin` and a concrete mixin class.")

                # add to each registry that the mixin supports
                for base in bases:

                    ## add mixin to parent registry
                    base.__registry__[name] = klass

                # add to global mixin lookup to prevent double loading
                cls._mixin_lookup.add(name)

                # see if we already have a compound class (mixins loaded after models)
                if Mixin._compound.get(cls):

                    ## extend class dict if we already have one
                    Mixin._compound.__dict__.update(dict(cls.__dict__.items()))

            return klass

        def __repr__(cls):

            ''' Generate a string representation of a `Mixin` subclass. '''

            return "<Mixin '%s.%s'>" % (cls.__module__, cls.__name__)

    internals = __metaclass__

    @decorators.classproperty
    def methods(cls):

        ''' Recursively return all available `Mixin` methods. '''

        for component in cls.components:
            for method, func in component.__dict__.items():
                yield method, func

    @decorators.classproperty
    def compound(cls):

        ''' Generate a compound mixin class. '''

        if isinstance(cls.__compound__, basestring):

            # if we've never generated a `CompoundModel` or if it's been changed, regenerate...
            cls.__compound__ = globals()[cls.__compound__] = cls.internals._compound[cls] = type(*(
                cls.__compound__,
                (cls, object),
                dict([
                    ('__origin__', cls),
                    ('__slots__', tuple()),
                ] + [(k, v) for k, v in cls.methods])
            ))

        return cls.__compound__

    @decorators.classproperty
    def components(cls):

        ''' Return the individual components of a composed `KeyMixin`. '''

        for mixin in cls.__registry__.itervalues(): yield mixin


## KeyMixin
# Extendable, registered class that mixes in attributes to `Key`.
class KeyMixin(Mixin):

    ''' Allows injection of attributes into `Key`. '''

    __slots__ = tuple()
    __compound__ = 'CompoundKey'
    __registry__ = Mixin._key_mixin_registry


## ModelMixin
# Extendable, registered class that mixes in attributes to `Model`.
class ModelMixin(Mixin):

    ''' Allows injection of attributes into `Model`. '''

    __slots__ = tuple()
    __compound__ = 'CompoundModel'
    __registry__ = Mixin._model_mixin_registry
