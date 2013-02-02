# -*- coding: utf-8 -*-

'''

Util: Datastructures

Holds useful classes and code for managing/manipulating/using specialized datastructures.

-sam (<sam@momentum.io>)

'''

# Base Imports
import abc
import logging


## Sentinel
# Small utility class used to create named marker objects.
class Sentinel(object):

    ''' Create a named sentinel object. '''

    name = None

    def __init__(self, name):

        ''' Construct a new sentinel. '''

        self.name = name

    def __repr__(self):

        ''' Represent this sentinel as a string. '''

        return '<Sentinel "%s">' % self.name

# Sentinels
_EMPTY, _TOMBSTONE = Sentinel("EMPTY"), Sentinel("TOMBSTONE")


## UtilStruct
# Base class for apptools' utility datastructures, which were shamelessly taken from [Providence/Clarity](http://github.com:sgammon/ProvidenceClarity)
class UtilStruct(object):

    ''' Abstract class for a utility object. '''

    _type = None

    ## Init -- Accept structure fill
    def __init__(self, struct=None, case_sensitive=True, **kwargs):

        ''' If handed a dictionary (or something) in init, send it to fillStructure (and do the same for kwargs). '''

        try:
            if struct is not None:
                self.fillStructure(struct, case_sensitive=case_sensitive)
            if len(kwargs) > 0:
                self.fillStructure(case_sensitive=case_sensitive, **kwargs)
        except TypeError:
            logging.critical('Type error encountered when trying to fillStructure.')
            logging.critical('Current struct: "%s".' % self)
            logging.critical('Target struct: "%s".' % struct)

    @classmethod
    def _type(cls):
        return cls._type

    def serialize(self):
        return self.__dict__

    @classmethod
    def deserialize(cls, structure):
        return cls(structure)


## DictProxy
# Take a data structure, and wrap it in an object so that it's accessible as ds[x] via getitem/setitem.
class DictProxy(UtilStruct):

    ''' Handy little object that takes a dict and makes it accessible via var[item] and var.item formats. Also handy for caching. '''

    ## Init
    def fillStructure(self, struct=None, case_sensitive=True, **kwargs):

        ''' Set it as an object directly instead of storing in _entries. '''

        if struct is not None:
            if isinstance(struct, dict):
                for k, v in struct.items():
                    if case_sensitive is False:
                        k = str(k).lower()
                    setattr(self, k, v)

            elif isinstance(struct, list):
                for k, v in struct:
                    if case_sensitive is False:
                        k = str(k).lower()
                    setattr(self, k, v)
        if len(kwargs) > 0:
            for k, v in kwargs.items():
                if case_sensitive is False:
                    k = str(k).lower()
                setattr(self, k, v)

    def __getitem__(self, name):
        if name in self.__dict__:
            return getattr(self, name)
        else:
            raise AttributeError

    def extend(self, obj):
        for name, value in obj.items():
            setattr(self, name, value)
        return

    def __setitem__(self, name, value):
        setattr(self, name, value)

    def __delitem__(self, name):
        if name in self.__dict__:
            del self.__dict__[name]
        else:
            raise AttributeError

    def __contains__(self, name):
        return name in self.__dict__

    ## Utiliy Methods
    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def items(self):
        return [(k, v) for k, v in self.__dict__.items()]

    def get(self, name, default_value=None):

        ''' Retrieve the named item, returning default_value if it cannot be found. '''

        if name in self.__dict__:
            return self.__dict__[name]
        else:
            return default_value


## ObjectProxy
# Take a datastructure and wrap it in an object that makes it accessible via ds.x, using getattr/setattr.
class ObjectProxy(UtilStruct):

    ''' Same handy object as above, but stores the entries in an _entries attribute rather than the class dict.  '''

    _entries = {}
    i_filter = lambda _, k: k

    def fillStructure(self, fill, case_sensitive=True, **kwargs):

        ''' If handed a dictionary or kwargs, fill _entries with e[k] = v. A list will do the same and be interpreted as a list of tuples in (k, v) format. '''

        if case_sensitive is False:
            self.i_filter = lambda k: str(k).lower()
        if fill is not None:
            if isinstance(fill, dict):
                for k, v in fill.items():
                    if case_sensitive is False:
                        k = str(k).lower()
                    self._entries[k] = v
            elif isinstance(fill, list):
                for k, v in fill:
                    if case_sensitive is False:
                        k = str(k).lower()
                    self._entries[k] = v
        if len(kwargs) > 0:
            for k, v in kwargs.items():
                if case_sensitive is False:
                    k = str(k).lower()
                self._entries[k] = v

    def __getitem__(self, name):
        if self.i_filter(name) in self._entries:
            return self._entries[self.i_filter(name)]
        else:
            raise KeyError

    def __delitem__(self, name):
        if self.i_filter(name) in self._entries:
            del self._entries[self.i_filter(name)]

    def __getattr__(self, name):
        if self.i_filter(name) in self._entries:
            return self._entries[self.i_filter(name)]
        else:
            raise AttributeError("Could not find the attribute '%s' on the specified ObjectProxy." % name)

    def __contains__(self, name):
        return self.i_filter(name) in self._entries

    def __delattr__(self, name):
        if self.i_filter(name) in self._entries:
            del self._entries[self.i_filter(name)]

    def keys(self):
        for entry in self._entries.keys():
            yield entry

    def values(self):
        for entry in self._entries.values():
            yield entry

    ## Utiliy Methods
    def items(self):
        for k, v in self._entries.items():
            yield (k, v)


## WritableObjectProxy
# Same handy class as above, but allows appending things at runtime.
class WritableObjectProxy(ObjectProxy):

    ''' Same handy object as `ObjectProxy`, but allows appending things at runtime. '''

    def __setitem__(self, name, value):
        self._entries[name] = value

    def __setattr__(self, name, value):
        self._entries[name] = value


## CallbackProxy
# Take a datastructure and wrap it in an object, such that when a key is requested via ds.x or ds[x], a function is called with that key's value, and provide the return value (i.e. return callback(d[x])).
class CallbackProxy(ObjectProxy):

    ''' Handy little object that takes a dict and makes it accessible via var[item], but returns the result of an invoked callback(item). '''

    _entries = None
    callback = None

    def __init__(self, callback, struct={}, **kwargs):

        ''' Map the callback and fillStructure if we get one via `struct`. '''

        self.callback = callback

        if struct is not None:
            self._entries = struct
        else:
            if len(kwargs) > 0:
                self._entries = dict([i for i in struct.items()] + [i for i in kwargs.items()])

    def __getitem__(self, name):
        if self._entries:
            if name in self._entries:
                return self.callback(self._entries.get(name))
            else:
                raise KeyError
        else:
            return self.callback(name)

    def __getattr__(self, name):
        if self._entries:
            if not name or (name not in self._entries):
                logging.debug('CallbackProxy entry pool: "%s".' % self._entries)
                raise AttributeError("CallbackProxy could not resolve entry '%s'." % name)
            return self.callback(self._entries.get(name))
        else:
            return self.callback(name)

    def __call__(self):
        return self.callback()


## ObjectDictBridge
# Treat an object like a dict, or an object!
class ObjectDictBridge(UtilStruct):

    ''' Treat an object like a dict, or an object! Assign an object with `ObjectDictBridge(<object>)`. Then access properties with `bridge[item]` or `bridge.item`. '''

    target = None

    def __init__(self, target_object=None):
        super(ObjectDictBridge, self).__setattr__('target', target_object)
        return

    def __getitem__(self, name):
        if self.target is not None:
            try:
                return getattr(self.target, name)
            except AttributeError, e:
                raise KeyError(str(e))
        else:
            raise KeyError('No object target set for ObjectDictBridge.')

    def __setitem__(self, name):
        if self.target is not None:
            try:
                return setattr(self.target, name)
            except Exception, e:
                raise e
        else:
            raise KeyError('No object target set for ObjectDictBridge.')

    def __delitem__(self, name):
        if self.target is not None:
            try:
                return delattr(self.target, name)
            except Exception, e:
                raise e
        else:
            raise KeyError('No object target set for ObjectDictBridge.')

    def __getattr__(self, name):
        if self.target is not None:
            try:
                return getattr(self.target, name)
            except Exception, e:
                raise e
        else:
            raise KeyError('No object target set for ObjectDictBridge.')

    def __setattr__(self, name):
        if self.target is not None:
            try:
                return setattr(self.target, name)
            except Exception, e:
                raise e
        else:
            raise KeyError('No object target set for ObjectDictBridge.')

    def __delattr__(self, name):
        if self.target is not None:
            try:
                return delattr(self.target, name)
            except Exception, e:
                raise e
        else:
            raise KeyError('No object target set for ObjectDictBridge.')

    def __contains__(self, name):

        ''' Indicates whether this ObjectDictBridge contains the given key. '''

        try:
            getattr(self.target, name)
        except AttributeError:
            return False
        return True

    def get(self, name, default_value=None):
        try:
            return getattr(self.target, name)
        except:
            return default_value
        return default_value


## StateManager
# Used in the service layer as a mixin for tracking object-level state.
class StateManager(object):

    ''' Addon class for managing a self.state property. '''

    def _setstate(self, key, value):

        ''' Set an item in service state. '''

        self.state['service'][key] = value
        return

    def _getstate(self, key, default):

        ''' Get an item from service state. '''

        if key in self.state['service']:
            return self.state['service'][key]
        else:
            return default

    def _delstate(self, key):

        ''' Delete an item from service state. '''

        if key in self.state['service']:
            del self.state['service'][key]

    def __setitem__(self, key, value):

        ''' `service[key] = value` syntax to set an item in service state. '''

        self._setstate(key, value)

    def __getitem__(self, key):

        ''' `var = service[key]` syntax to get an item from service state. '''

        return self._getstate(key, None)

    def __delitem__(self, key):

        ''' `del service[key] syntax` to delete an item from service state. '''

        self._delstate(key)


## ProxiedStructure
# Metaclass for doubly-indexed mappings. Used in BidirectionalEnum.
class ProxiedStructure(type):

    ''' Metaclass for property-gather-enabled classes. '''

    def __new__(cls, name, chain, mappings):

        ''' Read mapped properties, store on the object, along with a reverse mapping. '''

        if name == 'ProxiedStructure':
            return type(name, chain, mappings)

        # Init calculated data attributes
        mappings['_pmap'] = {}
        mappings['_plookup'] = []

        # Define __contains__ proxy
        def _contains(proxied_o, flag_or_value):

            ''' Bidirectionally-compatible __contains__ replacement. '''

            return flag_or_value in proxied_o._plookup

        # Define __getitem__ proxy
        def _getitem(proxied_o, fragment):

            ''' Attempt to resolve the fragment by a forward, then reverse resolution chain. '''

            if proxied_o.__contains__(fragment):

                return proxied_o._pmap.get(fragment)

        # Define __setitem__ proxy
        def _setitem(proxied_o, n, v):

            ''' Block setitem calls, because this is a complicated object that is supposed to be a modelling tool only. '''

            raise NotImplemented

        # Map properties into data and lookup attributes
        map(lambda x: [mappings['_pmap'].update(dict(x)), mappings['_plookup'].append([x[0][0], x[1][0]])],
            (((attr, value), (value, attr)) for attr, value in mappings.items() if not attr.startswith('_')))

        # Map methods
        mappings.update({
            '__getitem__': _getitem,
            '__setitem__': _setitem,
            '__contains__': _contains
        })

        new_cls = type(name, chain, mappings)
        return new_cls


## BidirectionalEnum
# Simple datastructure for mapping small / useful values to larger ones.
class BidirectionalEnum(object):

    ''' Small and simple datastructure for mapping static flags to smaller values. '''

    __singleton__ = True
    __metaclass__ = ProxiedStructure

    @classmethod
    def reverse_resolve(cls, code):

        ''' Resolve a mapping, by it's integer/string code. '''

        if code in cls._pmap:
            return cls._pmap[code]
        return False

    @classmethod
    def forward_resolve(cls, flag):

        ''' Resolve a mapping, by it's string property name. '''

        if flag in cls._pmap:
            return cls.__getattr__(flag)
        return False

    @classmethod
    def resolve(cls, flag): return cls.forward_resolve(flag)

    @classmethod
    def __serialize__(cls):

        ''' Flatten down into a structure suitable for storage/transport. '''

        return dict([(k, v) for k, v in dir(cls) if not k.startswith('_')])

    @classmethod
    def __json__(cls):

        ''' Flatten down and serialize into JSON. '''

        return cls.__serialize__()

    @classmethod
    def __repr__(cls):

        ''' Display a string representation of a flattened self. '''

        return '::'.join([
            "<%s" % self.__class__.__name__,
            ','.join([
                block for block in ('='.join([str(k), str(v)]) for k, v in cls.__serialize__().items())]),
            "BiDirectional>"
            ])


## TrackedDictionary
# Used in the upcoming Core Sessions API. Keeps track of an objects "dirtyness" (whether it has been modified since first population).
class TrackedDictionary(object):

    ''' Keeps track of modifications and modified state for a dictionary. '''

    __metaclass__ = abc.ABCMeta

    __data = {}
    __seen = set([])
    __dirty = None
    __target = None
    __failfast = False
    __mutations = []

    def __init__(self, initial={}, target=None):

        ''' Prepare internal data storage. '''

        self.__data, self.__dirty, self.__seen, self.__target, self.__mutations = initial, None, set([]), target, []

    def __getitem__(self, key, exception=KeyError):

        ''' Retrieve from internal storage. '''

        value = self.__data.get(key, _EMPTY)
        if value == _EMPTY:
            if self.__failfast:
                raise exception("TrackedDictionary could not resolve key '%s'." % key)
        return value

    def __setitem__(self, key, value):

        ''' Set a value in internal storage. '''

        self.__dirty = True
        self.__data[key] = value
        self.__seen.add(key)
        self.__mutations.append((key, value))

    def __delitem__(self, key, exception=KeyError):

        ''' Remove an item from internal storage. '''

        if key in self:
            self.__mutations.append((key, _TOMBSTONE))
            del self.__data[key]
            self.__dirty = True
            return
        raise exception("TrackedDictionary could not delete missing key '%s'." % key)

    def __nonzero__(self):

        ''' Indicates whether this dictionary is empty or not. '''

        return True if self._data else False

    def __contains__(self, key):

        ''' Indicate whether we have a key or not. '''

        return key in self.__seen

    def __len__(self):

        ''' Return the length of this TrackedDictionary. '''

        return len(self.__data)

    def __repr__(self):

        ''' Properly allow serialization. '''

        return self.__data.__repr__()

    def __iter__(self):

        ''' Iterate over keys in internal storage. '''

        for k in self.__data.iterkeys():
            yield k

    def __json__(self):

        ''' JSON hook. '''

        return self.__data

    @classmethod
    def __subclasshook__(cls, other):

        ''' Check if the provided object is a TrackedDictionary. '''

        if cls is TrackedDictionary:
            if any("reconcile" in i.__dict__ for i in other.__mro__):
                return True
        return NotImplemented

    @abc.abstractmethod
    def reconcile(self, target=None):

        ''' Flatten this object's mutation pool onto the target object. '''

        raise NotImplementedError

    def dirty(self):

        ''' Return this object's `dirty` status. '''

        return self.__dirty

    def mutations(self):

        ''' Return this object's mutation pool. '''

        return self.__mutations[:]

    def update(self, mapping):

        ''' Update internal values. '''

        if isinstance(mapping, list):
            mapping = dict(mapping)
        for k, v in mapping.items():
            self.__setitem__(k, v)
        return self.__data

    def items(self):

        ''' Return a list of (keys, values). '''

        return self.__data.items()

    def keys(self):

        ''' Return a list of all available keys. '''

        return self.__data.keys()

    def values(self):

        ''' Return a list of all available values. '''

        return self.__data.values()

    def iteritems(self):

        ''' Yield (keys, values) one at a time. '''

        for k, v in self.__data.iteritems():
            yield k, v

    def iterkeys(self):

        ''' Yield keys one at a time. '''

        for k in self.__data.iterkeys():
            yield k

    def itervalues(self):

        ''' Yield values one at a time. '''

        for v in self.__data.itervalues():
            yield v

    def get(self, key, default=None):

        ''' Retrieve an item, safely, optionally returning `default` if no item could be found. '''

        if self.__contains__(key):
            return self.__data.get(key, default)
        return default

    __setattr__ = __setitem__
    __getattr__ = lambda x, y: x.__getitem__(y)


## PropertyDescriptor - utility class for wrapping a value + type pair, with options
class PropertyDescriptor(object):

    ''' Utility class used to encapsulate a name, type, and set of options for a property on a data model. '''

    __null = True     # allow null values in this property
    __name = _EMPTY   # name of the property
    __type = _EMPTY   # basetype of the property
    __opts = _EMPTY   # options for implementation classes
    __value = _EMPTY  # the value of this property

    def __init__(self, name, proptype, options, **kwargs):

        ''' Property initialized and descriptor class. '''

        options.update(kwargs)
        self.__name, self.__type, self.__opts = name, proptype, DictProxy(options)

    def __set__(self, instance, value):

        ''' Set this property's internal value. '''

        # check type
        if 'validate' not in self.__opts and 'typeless' not in self.__opts and self.__opts.get('typeless', False) != True:
            if not isinstance(value, self.__type):
                if value == None and self.__null:
                    pass
                else:
                    raise ValueError('Property "%s" on model instance "%s" only accepts values of type "%s".' % (self.__name, instance, self.__type))
        else:
            if not self.__opts.get('typeless', False):
                value = self.__opts.validate(value)

        self.__value = value
        return

    def __get__(self, instance, owner):

        ''' Get this property's internal value. '''

        # if empty, return None
        if self.__value == _EMPTY:
            if hasattr(instance, '__sentinel__'):
                if instance.__sentinel__:
                    return _EMPTY
            return None
        else:
            return self.__value

    def __delete__(self, instance):

        ''' Delete this property's internal value. '''

        # set value to empty
        self.__value = _EMPTY
