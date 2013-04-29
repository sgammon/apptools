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

# apptools utils
from apptools.util import debug
from apptools.util import decorators
from apptools.util import datastructures

# Globals
_adapters = {}
_adapters_by_model = {}

# Computed Classes
CompoundKey = None
CompoundModel = None


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

        # resolve model class
        _model = self.registry.get(entity.kind())
        if not _model: raise ValueError('Could not resolve model class "%s".' % model.kind())

        # validate entity, will raise validation exceptions
        for name, value in entity.to_dict(_all=True).items(): _model.__dict__[name].valid(entity)

        # resolve key if we have a zero-y key or key class
        if not entity.key: entity.key = _model.__keyclass__(entity.kind(), self.allocate_ids(_model.__keyclass__, entity.kind()))  # build an ID-based key

        # flatten key/entity
        joined, flattened = entity.key.flatten(True)

        # delegate
        return self.put((self.encode_key(joined, flattened) or entity.key.urlsafe(joined), flattened), entity._set_persisted(True), _model)

    def _delete(self, key):

        ''' Internal method for deleting an entity by Key. '''

        joined, flattened = key.flatten(True)
        return self.delete((self.encode_key(joined, flattened) or key.urlsafe(joined), flattened))

    @classmethod
    def _register(cls, model):

        ''' Internal method for registering a Model class with this adapter's registry. '''

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

    def encode_key(cls, joined, flattened):  # pragma: no cover

        ''' Encode a Key for storage. '''

        return False  # by default, yield to key b64 builtin encoding


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
                    ## mixins are only allowed to _directly_ extend `KeyMixin` or `ModelMixin` - no midway classes.
                    raise RuntimeError("Cannot inject classes for inheritance in between `KeyMixin` or `ModelMixin` and a concrete mixin class.")
                else:
                    ## add mixin to parent registry
                    bases[0].__registry__[name] = klass
                    cls._mixin_lookup.add(name)

                if Mixin._compound.get(cls):
                    # extend class dict if we already have one
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
