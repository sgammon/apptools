# -*- coding: utf-8 -*-

# meta
__doc__ = '''

    apptools2: model API
    -------------------------------------------------
    |                                               |
    |   `apptools.model`                            |
    |                                               |
    |   a general-purpose, minimalist toolkit for   |
    |   extensible pythonic data modelling.         |
    |                                               |
    -------------------------------------------------
    |   authors:                                    |
    |       -- sam gammon (sam@momentum.io)         |
    -------------------------------------------------
    |   changelog:                                  |
    |       -- apr 1, 2013: initial draft           |
    |       -- may 7, 2013: refactor->v2, cleanup   |
    -------------------------------------------------

'''

__version__ = 'v2'

# stdlib
import abc
import operator

# app config
try:
    import config; _APPCONFIG = True
except ImportError as e:  # pragma: no cover
    _APPCONFIG = False

# apptools util
from apptools.util import json

# apptools model adapters
from .adapter import abstract, concrete
from .adapter import KeyMixin, ModelMixin

# apptools datastructures
from apptools.util.datastructures import _EMPTY

# === appengine NDB support === #
try:
    from google.appengine.ext import ndb as nndb

# if it's not available, redirect key/model parents to native <object>
except ImportError as e:
    _NDB, _key_parent, _model_parent = False, lambda: object, lambda: object

# if it *is* available, we need to inherit from NDB's key and model classes
else:  # pragma: no cover
    _NDB, _key_parent, _model_parent = True, lambda: nndb.Key, lambda: nndb.MetaModel


# Globals / Sentinels
_MULTITENANCY = False  # toggle multitenant key namespaces
_DEFAULT_KEY_SCHEMA = tuple(['id', 'kind', 'parent'])  # default schema for key classes
_MULTITENANT_KEY_SCHEMA = tuple(['id', 'kind', 'parent', 'namespace', 'app'])  # key schema for multitenancy-enabled apps


## == Metaclasses == ##

## MetaFactory
# Abstract metaclass parent that provides common construction methods.
class MetaFactory(type):

    ''' Abstract parent for model metaclasses. '''

    class __metaclass__(abc.ABCMeta):

        ''' Local metaclass for enforcing ABC compliance and __class__.__name__ formatting. '''

        __owner__ = 'MetaFactory'

        def __new__(cls, name=None, bases=tuple(), properties={}):

            ''' Factory for metaclasses classes. '''

            # if we're factory-ing an embedded metaclass, alias its name to its `__owner__` (for __repr__ clarity)
            if name == '__metaclass__' and hasattr(cls, '__owner__'):
                name = cls.__name__ = cls.__owner__
            return super(cls, cls).__new__(cls, name, bases, properties)  # pass up the chain properly to ensure metaclass enforcement

    ## = Internal Methods = ##
    def __new__(cls, name=None, bases=tuple(), properties={}):

        ''' Factory for model metaclasses. '''

        # fail on regular class construction - embedded metaclasses cannot be instantiated
        if not name:
            raise NotImplementedError('Cannot directly instantiate abstract class `MetaFactory`.')

        # pass up the inheritance chain to `type`, which properly enforces metaclasses
        impl = cls.initialize(name, bases, properties)
        if isinstance(impl, tuple):  # if we're passed a tuple, we're being asked to super-instantiate
            return super(MetaFactory, cls).__new__(cls, *impl)
        return impl

    ## = Exported Methods = ##
    @classmethod
    def resolve(cls, name, bases, properties, default=True):  # @TODO: clean up `resolve`

        ''' Resolve a suitable adapter set for a given class. '''

        if '__adapter__' not in properties:
            available_adapters = [option for option in concrete if option.is_supported()]  # grab each supported adapter

            # fail with no adapters...
            if not available_adapters:  # pragma: no cover
                raise RuntimeError('No valid model adapters found.')

            # if we only have one adapter, the choice is easy...
            if not default:
                return available_adapters[0].acquire(name, bases, properties), tuple()

            return available_adapters[0].acquire(name, bases, properties)

        # an explicit adapter was requested via an `__adapter__` class property
        for available in filter(lambda x: x is properties['__adapter__'] or x.__name__ == properties.get('__adapter__'), concrete):
            return available.acquire(name, bases, properties)
        raise RuntimeError("Requested model adapter \"%s\" could not be found or is not supported in this environment." % properties['__adapter__'])

    ## = Abstract Methods = ##
    @abc.abstractmethod
    def initialize(cls, name, bases, properties):  # pragma: no cover

        ''' Initialize a subclass. Must be overridden by child metaclasses. '''

        raise NotImplementedError('Classmethod `MetaFactory.initialize` must be overridden by subclasses and cannot be invoked directly.')


## == Abstract Classes == ##

## AbstractKey
# Metaclass for a datamodel key class.
class AbstractKey(_key_parent()):

    ''' Abstract Key class. '''

    ## = Encapsulated Classes = ##

    ## AbstractKey.__metaclass__
    # Constructs and prepares Key classes for use in the AppTools model subsystem.
    class __metaclass__(MetaFactory):

        ''' Metaclass for model keys. '''

        __owner__ = 'Key'
        __schema__ = _DEFAULT_KEY_SCHEMA

        @classmethod
        def initialize(cls, name, bases, properties):

            ''' Initialize a Key class. '''

            if name == 'AbstractKey':
                return name, bases, dict([(k, v) for k, v in [('__adapter__', cls.resolve(name, bases, properties))] + properties.items()])  # @TODO: convert to a dict comprehension someday

            key_class = [  # build initial key class structure
                ('__slots__', set()),  # seal object attributes, keys don't need any new space
                ('__bases__', bases),  # define bases for class
                ('__name__', name),  # set class name internals
                ('__owner__', None),  # reference to current owner entity, if any
                ('__adapter__', cls.resolve(name, bases, properties)),  # resolve adapter for key
                ('__persisted__', False) ]  # default to not knowing whether this key is persisted

            # add key format items, initted to None (doing this after adding the resolved adapter allows override via `__adapter__`) then return an argset for `type`
            return name, bases, dict([(k, v) for k, v in ([('__%s__' % x, None) for x in properties.get('__schema__', cls.__schema__)] + key_class + properties.items())])  # @TODO: convert to a dict comprehension someday

        def mro(cls):

            ''' Generate a fully-mixed method resolution order for `AbstractKey` subclasses. '''

            if cls.__name__ != 'AbstractKey':  # must be a string, when `AbstractKey` comes through it is not yet defined
                if cls.__name__ != 'Key':  # must be a string, same reason as above
                    return tuple([cls] + [i for i in cls.__bases__ if i not in (Key, AbstractKey)] + [Key, AbstractKey, KeyMixin.compound, object])
                return (cls, AbstractKey, KeyMixin.compound, object)  # inheritance for `Key`
            return (cls, KeyMixin.compound, object)  # inheritance for `AbstractKey`

        # util: generate string representation of a `Key` class, like "Key(<schema1>, <schema n...>)".
        __repr__ = lambda cls:  '%s(%s)' % (cls.__name__, ', '.join((i for i in reversed(cls.__schema__))))

    def __new__(cls, *args, **kwargs):

        ''' Intercepts construction requests for directly Abstract model classes. '''

        if cls.__name__ == 'AbstractKey':  # prevent direct instantiation of `AbstractKey`
            raise TypeError('Cannot directly instantiate abstract class `AbstractKey`.')
        return super(_key_parent(), cls).__new__(*args, **kwargs)  # pragma: no cover

    def __eq__(self, other):

        ''' Test whether two keys are functionally identical. '''

        if not other: return other  # make sure the other entity isn't falsy
        if len(self.__schema__) != len(other.__schema__) or not isinstance(other, self.__class__): return False  # if schemas don't match it's falsy
        return all([i for i in map(lambda x: hasattr(other, x) and (getattr(other, x) == getattr(self, x)), self.__schema__)])  # if values don't match it's falsy

    def __repr__(self):

        ''' Generate a string representation of this Key. '''

        return "%s(%s)" % (self.__class__.__name__, ', '.join((('%s=%s' % (k, getattr(self, k)) for k in reversed(self.__schema__)))))

    # util: alias `__repr__` to string magic methods
    __str__ = __unicode__ = __repr__

    # util: support for `__nonzero__` and aliased `__len__` (returns dirtyness and written-to properties, respectively)
    __nonzero__ = lambda self: isinstance(self.__id__, (basestring, str, int, unicode))
    __len__ = lambda self: (int(self.__nonzero__()) if self.__parent__ is None else sum((1 for i in self.ancestry)))

    ## = Property Setters = ##
    def _set_internal(self, name, value):

        ''' Set an internal property on a `Key`. '''

        # fail if we're already persisted, unless we're setting a reference to the current owner
        if self.__persisted__ and name != 'owner':
            raise AttributeError("Cannot set property \"%s\" of an already-persisted key." % name)
        setattr(self, '__%s__' % name, value)
        return self

    ## = Property Getters = ##
    def _get_ancestry(self):

        ''' Retrieve this Key's ancestry path. '''

        if self.__parent__:  # if we have a parent, yield upward
            for i in self.__parent__.ancestry:
                yield i

        yield self  # yield self to signify the end of the chain, and stop iteration
        raise StopIteration()

    ## = Property Bindings  = ##
    id = property(lambda self: self.__id__, lambda self, id: self._set_internal('id', id))
    app = property(lambda self: self.__app__, lambda self, app: self._set_internal('app', app))
    kind = property(lambda self: self.__kind__, lambda self, kind: self._set_internal('kind', kind))
    owner = property(lambda self: self.__owner__, None)  # restrict writing to `owner`
    parent = property(lambda self: self.__parent__, lambda self, parent: self._set_internal('parent', parent))
    ancestry = property(_get_ancestry, None)  # no writing to `ancestry` (derived)
    namespace = property(lambda self: self.__namespace__ if _MULTITENANCY else None, lambda self, ns: self._set_internal('namespace', ns) if _MULTITENANCY else None)


## AbstractModel
# Metaclass for a datamodel class.
class AbstractModel(_model_parent()):

    ''' Abstract Model class. '''

    __slots__ = tuple()

    ## = Encapsulated Classes = ##

    ## AbstractModel.__metaclass__
    # Initializes class-level property descriptors and re-writes model internals.
    class __metaclass__(MetaFactory):

        ''' Metaclass for data models. '''

        __owner__ = 'Model'

        @classmethod
        def initialize(cls, name, bases, properties):

            ''' Initialize a Model class. '''

            if name not in frozenset(['AbstractModel', 'Model']):  # core model classes come through here before being defined - must use string name :(

                property_map = {}  # parse property spec (`name = <basetype>` or `name = <basetype>, <options>`)

                for prop, spec in filter(lambda x: not x[0].startswith('_'), properties.iteritems()): # model properties that start with '_' are ignored

                    # build a descriptor object and data slot
                    basetype, options = (spec, {}) if not isinstance(spec, tuple) else spec
                    property_map[prop] = Property(prop, basetype, **options)

                if len(bases) > 1 or bases[0] != Model:  # merge and clone all basemodel properties, update dictionary with property map

                    property_map = dict([(key, value) for key, value in reduce(lambda left, right: left + right,
                                        [[(base_prop, base.__dict__[base_prop].clone()) for base_prop in base.__lookup__] for base in bases] + [property_map.items()])])

                prop_lookup = frozenset(property_map.keys())  # freeze property lookup
                model_adapter = cls.resolve(name, bases, properties)  # resolve default adapter for model

                modelclass = {  # build class layout, initialize core model class attributes.
                    '__impl__': {},  # holds cached implementation classes generated from this model
                    '__name__': name,  # map-in internal class name (should be == to Model kind)
                    '__kind__': name,  # kindname defaults to model class name (keep track of it here so we have it if __name__ changes)
                    '__bases__': bases,  # stores a model class's bases, so proper MRO can work
                    '__lookup__': prop_lookup,  # frozenset of allocated attributes, for quick lookup
                    '__adapter__': model_adapter,  # resolves default adapter class for this key/model
                    '__slots__': tuple() }  # seal-off object attributes (but allow weakrefs and explicit flag)

                modelclass.update(property_map)  # update at class-level with descriptor map
                impl = super(MetaFactory, cls).__new__(cls, name, bases, modelclass)  # inject our own property map, pass-through to `type`
                return impl.__adapter__._register(impl)

            return name, bases, properties  # pass-through to `type`

        def mro(cls):

            ''' Generate a fully-mixed method resolution order for `AbstractModel` subclasses. '''

            if cls.__name__ != 'AbstractModel':  # must be a string, when `AbstractModel` comes through it is not yet defined
                if cls.__name__ != 'Model':  # must be a string, same reason as above
                    return tuple([cls] + [i for i in cls.__bases__ if i not in (Model, AbstractModel)] + [Model, AbstractModel, ModelMixin.compound, object])
                return (cls, AbstractModel, ModelMixin.compound, object)  # inheritance for `Key`
            return (cls, ModelMixin.compound, object)  # inheritance for `AbstractKey`

        # util: generate string representation of `Model` class, like "Model(<prop1>, <prop n...>)".
        __repr__ = lambda cls: '%s(%s)' % (cls.__name__, ', '.join((i for i in cls.__lookup__)))

        def __setattr__(cls, name, value, exception=AttributeError):

            ''' Disallow property mutation before instantiation. '''

            if name in cls.__lookup__:  # cannot mutate data properties before instantiation
                raise exception("Cannot mutate property \"%s\" of model \"%s\" before instantiation." % (name, cls))
            if name.startswith('__'):
                return super(AbstractModel.__metaclass__, cls).__setattr__(name, value)

            # cannot create new properties before (or really after, except if you use an `Expando`) instantiation
            raise exception("Cannot create model property at name \"%s\" of model \"%s\" before instantiation." % (name, cls))


    ## AbstractModel.PropertyValue
    # Small, ultra-lightweight datastructure responsible for holding a property value bundle for an entity attribute.
    class _PropertyValue(tuple):

        ''' Named-tuple class for property value bundles. '''

        __slots__ = tuple()
        __fields__ = ('dirty', 'data')

        def __new__(_cls, data, dirty=False):

            ''' Create a new `PropertyValue` instance. '''

            return tuple.__new__(_cls, (data, dirty))  # pass up-the-chain to `tuple`

        # util: generate a string representatin of this `_PropertyValue`
        __repr__ = lambda self: "Value(%s)%s" % (('"%s"' % self[0]) if isinstance(self[0], basestring) else self[0].__repr__(), '*' if self[1] else '')

        # util: reduce arguments for pickle
        __getnewargs__ = lambda self: tuple(self)

        # util: lock down classdict
        __dict__ = property(lambda self: dict(zip(self.__fields__, self)))

        # util: map data and dirty properties
        data = property(operator.itemgetter(0), doc='Alias for `PropertyValue.data` at index 0.')
        dirty = property(operator.itemgetter(1), doc='Alias for `PropertyValue.dirty` at index 1.')

    # = Internal Methods = #
    def __new__(cls, *args, **kwargs):

        ''' Intercepts construction requests for directly Abstract model classes. '''

        if cls.__name__ == 'AbstractModel':  # prevent direct instantiation
            raise TypeError('Cannot directly instantiate abstract class `AbstractModel`.')
        return super(AbstractModel, cls).__new__(cls, *args, **kwargs)

    # util: generate a string representation of this entity, alias to string conversion methods too
    __repr__ = lambda self: "%s(%s, %s)" % (self.__kind__, self.__key__, ', '.join(['='.join([k, str(self.__data__.get(k, None))]) for k in self.__lookup__]))
    __str__ = __unicode__ = __repr__

    def __setattr__(self, name, value, exception=AttributeError):

        ''' Attribute write override. '''

        # internal properties, data properties and `key` can be written to after construction
        if name.startswith('__') or name in self.__lookup__ or name == 'key':
            return super(AbstractModel, self).__setattr__(name, value)  # delegate upwards for write
        raise exception("Cannot set nonexistent data property \"%s\" of model class \"%s\"." % (name, self.kind()))

    def __getitem__(self, name):

        ''' Item getter support. '''

        if name not in self.__lookup__:  # only data properties are exposed via `__getitem__`
            raise KeyError("Cannot get nonexistent data property \"%s\" of model class \"%s\"." % (name, self.kind()))
        return getattr(self, name)  # proxy to attribute API

    # util: support for python's item API
    __setitem__ = lambda self, item, value: self.__setattr__(item, value, KeyError)

    def __context__(self, _type=None, value=None, traceback=None):

        ''' Context enter/exit - apply explicit mode. '''

        if traceback:  # pragma: no cover
            return False  # in the case of an exception in-context, bubble it up
        self.__explicit__ = (not self.__explicit__)  # toggle explicit status
        return self

    # util: alias context entry/exit to `__context__` toggle method
    __enter__ = __exit__ = __context__

    # util: proxy `len` to length of written data (also alias `__nonzero__`)
    __len__ = lambda self: len(self.__data__)
    __nonzero__ = __len__

    # util: `dirty` property flag, proxies to internal `_PropertyValue`(s) for dirtyness
    __dirty__ = property(lambda self: any((dirty for value, dirty in self.__data__.itervalues())))

    # util: `persisted` property flag, indicates whether internal key has been persisted in storage
    __persisted__ = property(lambda self: self.key.__persisted__)

    def __iter__(self):

        ''' Allow models to be used as dict-like generators. '''

        for name in self.__lookup__:
            value = self._get_value(name, default=Property._sentinel)

            # skip unset properties without a default, except in `explicit` mode
            if (value == Property._sentinel and (not self.__explicit__)):
                if self.__class__.__dict__[name]._default != Property._sentinel:
                    yield name, self.__class__.__dict__[name]._default  # return a property's default in `implicit` mode, if any
                continue  # pragma: no cover
            yield name, value
        raise StopIteration()

    def _set_persisted(self, flag=False):

        ''' Notify this entity that it has been persisted to storage. '''

        self.key.__persisted__ = True
        for name in self.__data__:  # iterate over set properties
            # set value to previous, with `False` dirty flag
            self._set_value(name, self._get_value(name, default=Property._sentinel), False)
        return self

    def _get_value(self, name, default=None):

        ''' Retrieve the value of a named property on this Entity. '''

        if name:  # calling with no args gives all values in (name, value) form
            if name in self.__lookup__:
                value = self.__data__.get(name, Property._sentinel)
                if not value:
                    if self.__explicit__ and value is Property._sentinel:
                        return Property._sentinel  # return system _EMPTY sentinel in explicit mode, if property is unset
                    return default  # return default value passed in
                return value.data  # return property value
            raise AttributeError("Model \"%s\" has no property \"%s\"." % (self.kind(), name))
        return [(i, getattr(self, i)) for i in self.__lookup__]

    def _set_value(self, name, value=_EMPTY, _dirty=True):

        ''' Set (or reset) the value of a named property on this Entity. '''

        if not name: return self  # empty strings or dicts or iterables return self

        if isinstance(name, (list, dict)):
            if isinstance(name, dict):
                name = name.items()  # convert dict to list of tuples
            return [self._set_value(k, i, _dirty=_dirty) for k, i in name if k not in ('key', '_persisted')]  # filter out flags from caller

        if isinstance(name, tuple):  # pragma: no cover
            name, value = name  # allow a tuple of (name, value), for use in map/filter/etc

        if name == 'key':  # if it's a key, set through _set_key
            return self._set_key(value).owner  # returns `self` :)

        if name in self.__lookup__:  # check property lookup
            self.__data__[name] = self.__class__._PropertyValue(value, _dirty)  # if it's a valid property, create a namedtuple value placeholder
            return self
        raise AttributeError("Model \"%s\" has no property \"%s\"." % (self.kind(), name))

    def _set_key(self, value=None, **kwargs):

        ''' Set this Entity's key manually. '''

        # cannot provide both a value and formats
        if value and kwargs:
            raise TypeError('Cannot merge multiple key values/formats in `%s._set_key`. (got: value(%s), formats(%s)).' % (self.kind(), value, kwargs))

        # for a literal key value
        if value is not None:
            if not isinstance(value, (self.__class__.__keyclass__, tuple, basestring)):  # filter out invalid key types
                raise TypeError('Cannot set model key to invalid type \"%s\" (for value \"%s\"). Expected `basestring`, `tuple` or `%s`.' % (type(value), value, self.__class__.__keyclass__.__name__))

            self.__key__ = {  # set local key from result of dict->get(<formatter>)->__call__(<value>)

                self.__class__.__keyclass__: lambda x: x,  # return keys directly
                tuple: self.__class__.__keyclass__.from_raw,  # pass tuples through `from_raw`
                basestring: self.__class__.__keyclass__.from_urlsafe  # pass strings through `from_urlsafe`

            }.get(type(value), lambda x: x)(value)._set_internal('owner', self)  # resolve by value type and execute

            return self.__key__  # return key

        if kwargs:  # filter out multiple formats
            formatter, value = kwargs.items()[0]
            if len(kwargs) > 1:  # disallow multiple format kwargs
                raise TypeError("Cannot provide multiple formats to `_set_key` (got: \"%s\")." % ', '.join(kwargs.keys()))

            self.__key__ = {  # resolve key converter, if any, set owner, and `__key__`, and return

                'raw': self.__class__.__keyclass__.from_raw,  # for raw, pass through `from_raw`
                'urlsafe': self.__class__.__keyclass__.from_urlsafe,  # for strings, pass through `from_urlsafe`
                'constructed': lambda x: x  # by default it's a constructed key

            }.get(formatter, lambda x: x)(value)._set_internal('owner', self)
            return self.__key__

        # except in the case of a null value and no formatter args (completely empty `_set_key`)
        raise TypeError("Could not operate on undefined key (value: \"%s\", kwargs: \"%s\")." % (value, kwargs))  # fail if we don't have a key at all

    ## = Property Bindings  = ##
    key = property(lambda self: self.__key__, _set_key)  # bind model key


## == Concrete Classes == ##

## Key
# Model datastore key concrete class.
class Key(AbstractKey):

    ''' Concrete Key class. '''

    __separator__ = u':'  # separator for joined/encoded keys
    __schema__ = _DEFAULT_KEY_SCHEMA if not _MULTITENANCY else _MULTITENANT_KEY_SCHEMA

    ## = Internal Methods = ##
    def __new__(cls, *parts, **formats):

        ''' Constructs keys from various formats. '''

        formatter, value = formats.items()[0] if formats else ('__constructed__', None)   # extract first provided format

        if len(formats) > 1:  # disallow multiple key formats
            raise TypeError("Cannot pass multiple formats into `Key` constructor. Received: \"\"." % ', '.join(formats))

        return {  # delegate full-key decoding to classmethods
            'raw': cls.from_raw,
            'urlsafe': cls.from_urlsafe
        }.get(formatter, lambda x: super(AbstractKey, cls).__new__(cls, *parts, **formats))(value)

    def __init__(self, *parts, **kwargs):

        ''' Initialize this Key. '''

        if len(parts) > 1:  # normal case: it's a full/partially-spec'd key

            if len(parts) <= len(self.__schema__):  # it's a fully- or partially-spec'ed key
                mapped = zip([i for i in reversed(self.__schema__)][(len(self.__schema__) - len(parts)):], map(lambda x: x.kind() if hasattr(x, 'kind') else x, parts))

            else:
                # for some reason the schema falls short of our parts
                raise TypeError("Key type \"%s\" takes a maximum of %s positional arguments to populate the format \"%s\"." % (self.__class__.__name__, len(self.__schema__), str(self.__schema__)))

            for name, value in map(lambda x: (x[0], x[1].kind()) if isinstance(x[1], Model) else x, mapped):
                setattr(self, name, value)  # set appropriate attribute via setter

        elif len(parts) == 1:  # special case: it's a kinded, empty key
            if hasattr(parts[0], 'kind'):
                parts = (parts[0].kind(),)  # quick ducktyping: is it a model? (don't yell at me, `issubclass` only supports classes)
            self.__kind__ = parts[0]

        # if we *know* this is an existing key, `_persisted` should be `true`. also set kwarg-passed parent.
        self._set_internal('parent', kwargs.get('parent'))._set_internal('persisted', kwargs.get('_persisted', False))


## Property
# Data-descriptor property class.
class Property(object):

    ''' Concrete Property class. '''

    __metaclass__ = abc.ABCMeta  # enforce definition of `validate` for subclasses
    __slots__ = ('name', '_options', '_indexed', '_required', '_repeated', '_basetype', '_default')
    _sentinel = _EMPTY  # default sentinel for basetypes/values (read only, since it isn't specified in `__slots__`)

    ## = Internal Methods = ##
    def __init__(self, name, basetype, default=_sentinel, required=False, repeated=False, indexed=True, **options):

        ''' Initialize this Property. '''

        # copy locals specified above onto object properties of the same name, specified in `self.__slots__`
        map(lambda args: setattr(self, *args), zip(self.__slots__, (name, options, indexed, required, repeated, basetype, default)))

    ## = Descriptor Methods = ##
    def __get__(self, instance, owner):

        ''' Descriptor attribute access. '''

        if instance:  # proxy to internal entity method.

            # grab value, returning special a) property default or b) sentinel if we're in explicit mode and it is unset
            if self._default != Property._sentinel:  # we have a set default
                value = instance._get_value(self.name, default=self._default)
            else:
                value = instance._get_value(self.name, default=Property._sentinel)

            if not value and value == Property._sentinel and instance.__explicit__ == False:
                return None  # soak up sentinels via the descriptor API
            return value

        elif self._default:  # if we have a default and we're at the class level, who cares just give it up i guess
            return self._default
        return None # otherwise, class-level access is always None

    def __set__(self, instance, value):

        ''' Descriptor attribute write. '''

        if instance is not None:  # only allow data writes after instantiation
            return instance._set_value(self.name, value)  # delegate to `AbstractModel._set_value`
        raise AttributeError("Cannot mutate model property \"%s\" before instantiation." % self.name)

    __delete__ = lambda self, instance: instance.__set__(instance, None)  # delegate to `__set__` with a `None`-value, which clears it

    def valid(self, instance):

        ''' Validate the value of this property, if any. '''

        if self.__class__ != Property and hasattr(self, 'validate'):  # pragma: no cover
            return self.validate(instance)  # check for subclass-defined validator to delegate validation to

        value = instance._get_value(self.name)  # retrieve value

        if (value in (None, Property._sentinel)):
            if self._required:  # check required-ness
                raise ValueError("Property \"%s\" of Model class \"%s\" is marked as `required`, but was left unset." % (self.name, instance.kind()))
            return True  # empty value, non-required, all good :)

        if isinstance(value, (list, tuple, set, frozenset, dict)):  # check multi-ness
            if not self._repeated:
                raise ValueError("Property \"%s\" of Model class \"%s\" is not marked as repeated, and cannot accept iterable values." % (self.name, instance.kind()))
        else:
            if self._repeated:
                raise ValueError("Property \"%s\" of Model class \"%s\" is marked as iterable, and cannot accept non-iterable values." % (self.name, instance.kind()))
            value = (value,)  # make value iterable

        for v in value:  # check basetype
            if v is not Property._sentinel and (self._basetype not in (Property._sentinel, None) and isinstance(v, self._basetype)):
                continue  # valid instance of basetype
            raise ValueError("Property \"%s\" of Model class \"%s\" cannot accept value of type \"%s\" (was expecting type \"%s\")." % (self.name, instance.kind(), type(v).__name__, self._basetype.__name__))
        return True  # validation passed! :)

    # util method to clone `Property` objects
    clone = lambda self: self.__class__(self.name, self._basetype, self._default, self._required, self._repeated, self._indexed, **self._options)


## Model
# Concrete class for a data model.
class Model(AbstractModel):

    ''' Concrete Model class. '''

    __keyclass__ = Key

    ## = Internal Methods = ##
    def __init__(self, **properties):

        ''' Initialize this Model. '''

        # grab key / persisted flag, if any, and set explicit flag to `False`
        key, persisted, self.__explicit__ = properties.get('key', False), properties.get('_persisted', False), False

        # if we're handed a key, it's manually set... otherwise, build empty, kinded key
        self.key = key or self.__keyclass__(self.kind(), _persisted=False)

        # initialize internals and map any kwargs into data
        self.__data__, self.__initialized__ = {}, True
        self._set_value(properties, _dirty=(not persisted))

    ## = Class Methods = ##
    kind = classmethod(lambda cls: cls.__name__)


# Module Globals
__abstract__ = [abstract, MetaFactory, AbstractKey, AbstractModel]
__concrete__ = [concrete, Property, KeyMixin, ModelMixin, Key, Model]
__all__ = __abstract__ + __concrete__


if __name__ == '__main__':  # pragma: no cover

    # if run directly, run testsuite.
    from apptools import tests
    tests.run(tests.load('apptools.tests.test_model'))
