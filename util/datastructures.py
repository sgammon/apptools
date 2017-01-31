# -*- coding: utf-8 -*-

'''

    apptools util: datastructures

    holds useful classes and code for managing/manipulating/using specialized datastructures.

    :author: Sam Gammon <sam@momentum.io>
    :copyright: (c) momentum labs, 2013
    :license: The inspection, use, distribution, modification or implementation
              of this source code is governed by a private license - all rights
              are reserved by the Authors (collectively, "momentum labs, ltd")
              and held under relevant California and US Federal Copyright laws.
              For full details, see ``LICENSE.md`` at the root of this project.
              Continued inspection of this source code demands agreement with
              the included license and explicitly means acceptance to these terms.

'''


# Base Imports
import abc
import logging


class Sentinel(object):

    ''' Create a named sentinel object. '''

    name = None
    _falsy = False
    _fake_instance = None

    def __init__(self, name, falsy=False):

        ''' Construct a new sentinel.

            :param name:
            :param falsy:
            :returns: '''

        self.name, self._falsy = name, falsy

    def __repr__(self):

        ''' Represent this sentinel as a string.

            :returns: '''

        return '<Sentinel "%s">' % self.name

    def __nonzero__(self):

        ''' Test whether this sentinel is falsy.

            :returns: '''

        return (not self._falsy)


# Sentinels
_EMPTY, _TOMBSTONE = Sentinel("EMPTY", True), Sentinel("TOMBSTONE", True)


class UtilStruct(object):

    ''' Abstract class for a utility object. '''

    _type = None

    ## Init -- Accept structure fill
    def __init__(self, struct=None, case_sensitive=True, **kwargs):

        ''' If handed a dictionary (or something) in init, send it to
            fillStructure (and do the same for kwargs).

            :param struct:
            :param case_sensitive:
            :param kwargs:
            :raises TypeError:
            :returns: '''

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

        ''' Not sure what this is for (@sgammon)

            :returns: '''

        return cls._type

    def serialize(self):

        ''' Returns flattened version of self.

            :returns: '''

        return self.__dict__

    @classmethod
    def deserialize(cls, structure):

        ''' Builds ``structure`` into a ``cls``.

            :param structure:
            :returns: '''

        return cls(structure)


class DictProxy(UtilStruct):

    ''' Handy little object that takes a dict and makes it accessible
        via var[item] and var.item formats. Also handy for caching. '''

    ## Init
    def fillStructure(self, struct=None, case_sensitive=True, **kwargs):

        ''' Set it as an object directly instead of storing in _entries.

            :param struct:
            :param case_sensitive:
            :pwaram kwargs:
            :raises AttributeError:
            :returns: '''

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

        ''' 'x = struct[item]' override.

            :param name:
            :raises AttributeError:
            :returns: '''

        if name in self.__dict__:
            return getattr(self, name)
        else:
            raise AttributeError

    def extend(self, obj):

        ''' extend a struct.

            :param obj:
            :returns: '''

        for name, value in obj.items():
            setattr(self, name, value)
        return

    def __setitem__(self, name, value):

        ''' 'struct[item] = x' override.

            :param name:
            :param value:
            :returns: '''

        setattr(self, name, value)

    def __delitem__(self, name):

        ''' 'del struct[item]' override.

            :param name:
            :param value:
            :returns: '''

        if name in self.__dict__:
            del self.__dict__[name]
        else:
            raise AttributeError

    def __contains__(self, name):
        return name in self.__dict__

    ## Utiliy Methods
    def keys(self):

        ''' get all keys from this struct.

            :returns: '''

        return self.__dict__.keys()

    def values(self):

        ''' get all values from this struct.

            :returns: '''

        return self.__dict__.values()

    def items(self):

        ''' get all tupled (k, v) pairs from this struct.

            :returns: '''

        return [(k, v) for k, v in self.__dict__.items()]

    def get(self, name, default_value=None):

        ''' Retrieve the named item, returning default_value
            if it cannot be found.

            :param name:
            :param default_value:
            :returns: '''

        if name in self.__dict__:
            return self.__dict__[name]
        else:
            return default_value


class ObjectProxy(UtilStruct):

    ''' Same handy object as above, but stores the entries in an
        _entries attribute rather than the class dict.  '''

    _entries = {}
    i_filter = lambda _, k: k

    def fillStructure(self, fill, case_sensitive=True, **kwargs):

        ''' If handed a dictionary or kwargs, fill _entries with e[k] = v.
            A list will do the same and be interpreted as a list of tuples in (k, v) format.

            :param fill:
            :param case_sensitive:
            :param kwargs:
            :returns: '''

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

        ''' 'x = struct[name]' override.

            :param name:
            :raises KeyError:
            :returns: '''

        if self.i_filter(name) in self._entries:
            return self._entries[self.i_filter(name)]
        else:
            raise KeyError

    def __delitem__(self, name):

        ''' 'del struct[name]' override.

            :param name:
            :raises KeyError:
            :returns: '''

        if self.i_filter(name) in self._entries:
            del self._entries[self.i_filter(name)]
        raise KeyError("Could not find the entry '%s' on the specified ObjectProxy." % name)

    def __getattr__(self, name):

        ''' 'x = struct.name' override.

            :param name:
            :raises AttributeError
            :returns: '''

        if self.i_filter(name) in self._entries:
            return self._entries[self.i_filter(name)]
        raise AttributeError("Could not find the attribute '%s' on the specified ObjectProxy." % name)

    def __contains__(self, name):

        ''' 'x in struct' override.

            :param name:
            :returns: '''

        return self.i_filter(name) in self._entries

    def __delattr__(self, name):

        ''' 'del struct.name' override.

            :param name:
            :raises AttributeError:
            :returns: '''

        if self.i_filter(name) in self._entries:
            del self._entries[self.i_filter(name)]
        raise AttributeError("Could not find the entry '%s' on the specified ObjectProxy." % name)

    def keys(self):

        ''' return all keys in this struct.

            :returns: '''

        return self._entries.keys()

    def values(self):
        
        ''' return all values in this struct.

            :returns: '''

        self._entries.values()

    ## Utiliy Methods
    def items(self):

        ''' return all (k, v) pairs in this struct.

            :returns: '''

        return self._entries.items()


class WritableObjectProxy(ObjectProxy):

    ''' Same handy object as `ObjectProxy`, but allows appending things at runtime. '''

    def __setitem__(self, name, value):

        ''' 'struct[name] = x' override.

            :param name:
            :param value:
            :returns: '''

        self._entries[name] = value

    def __setattr__(self, name, value):

        ''' 'struct.name = x' override.

            :param name:
            :param value:
            :returns: '''

        self._entries[name] = value


class CallbackProxy(ObjectProxy):

    ''' Handy little object that takes a dict and makes
        it accessible via var[item], but returns the
        result of an invoked ``callback(item)``. '''

    _entries = None  # cached entries
    callback = None  # callback func

    def __init__(self, callback, struct={}, **kwargs):

        ''' Map the callback and fillStructure if we
            get one via `struct`.

            :param callback:
            :param struct:
            :param kwargs:
            :returns: '''

        self.callback = callback

        if struct is not None:
            self._entries = struct
        else:
            if len(kwargs) > 0:
                self._entries = dict([i for i in struct.items()] + [i for i in kwargs.items()])

    def __getitem__(self, name):

        ''' 'x = struct[name]' override.

            :param name:
            :raises KeyError:
            :returns: '''

        if self._entries:
            if name in self._entries:
                return self.callback(self._entries.get(name))
            else:
                raise KeyError
        else:
            return self.callback(name)

    def __getattr__(self, name):

        ''' 'x = struct.name' override.

            :param name:
            :raises AttributeError:
            :returns: '''

        if self._entries:
            if not name or (name not in self._entries):
                logging.debug('CallbackProxy entry pool: "%s".' % self._entries)
                raise AttributeError("CallbackProxy could not resolve entry '%s'." % name)
            return self.callback(self._entries.get(name))
        else:
            return self.callback(name)

    def __call__(self):

        ''' 'struct()' override.

            :returns: '''

        return self.callback()


class ObjectDictBridge(UtilStruct):

    ''' Treat an object like a dict, or an object! Assign an object
        with `ObjectDictBridge(<object>)`. Then access properties
        with `bridge[item]` or `bridge.item`. '''

    target = None  # target object

    def __init__(self, target_object=None):

        ''' constructor.

            :param target_object:
            :returns: '''

        super(ObjectDictBridge, self).__setattr__('target', target_object)

    def __getitem__(self, name):

        ''' 'x = struct[name]' override.

            :param name:
            :raise KeyError:
            :returns: '''

        if self.target is not None:
            try:
                return getattr(self.target, name)
            except AttributeError, e:
                raise KeyError(str(e))
        else:
            raise KeyError('No object target set for ObjectDictBridge.')

    def __setitem__(self, name):

        ''' 'struct[name] = x' override.

            :param name:
            :raises KeyError:
            :returns: '''

        if self.target is not None:
            try:
                return setattr(self.target, name)
            except Exception, e:
                raise e
        else:
            raise KeyError('No object target set for ObjectDictBridge.')

    def __delitem__(self, name):

        ''' 'del struct[name]' override.

            :param name:
            :raises KeyError:
            :raises AttributeError:
            :returns: '''

        if self.target is not None:
            try:
                return delattr(self.target, name)
            except Exception, e:
                raise e
        else:
            raise KeyError('No object target set for ObjectDictBridge.')

    def __getattr__(self, name):

        ''' 'x = struct.name' override.

            :param name:
            :raises KeyError:
            :raises AttributeError:
            :returns: '''

        if self.target is not None:
            try:
                return getattr(self.target, name)
            except Exception, e:
                raise e
        else:
            raise KeyError('No object target set for ObjectDictBridge.')

    def __setattr__(self, name):

        ''' 'struct.name = x' override.

            :param name:
            :raises KeyError:
            :raises AttributeError:
            :returns: '''

        if self.target is not None:
            try:
                return setattr(self.target, name)
            except Exception, e:
                raise e
        else:
            raise KeyError('No object target set for ObjectDictBridge.')

    def __delattr__(self, name):

        ''' 'del struct.name' override.

            :param name:
            :raises KeyError:
            :raises AttributeError:
            :returns: '''

        if self.target is not None:
            try:
                return delattr(self.target, name)
            except Exception, e:
                raise e
        else:
            raise KeyError('No object target set for ObjectDictBridge.')

    def __contains__(self, name):

        ''' Indicates whether this ObjectDictBridge
            contains the given key.

            :param name:
            :returns: '''

        try:
            getattr(self.target, name)
        except AttributeError:
            return False
        return True

    def get(self, name, default_value=None):

        ''' dict-like safe get (`obj.get(name, default)`).

            :param name:
            :param default_value:
            :returns: '''

        try:
            return getattr(self.target, name)
        except:
            return default_value
        return default_value


class StateManager(object):

    ''' Addon class for managing a self.state property. '''

    def _setstate(self, key, value):

        ''' Set an item in service state.

            :param key:
            :param value:
            :returns: '''

        self.state['service'][key] = value
        return

    def _getstate(self, key, default):

        ''' Get an item from service state.

            :param key:
            :param default:
            :returns: '''

        if key in self.state['service']:
            return self.state['service'][key]
        else:
            return default

    def _delstate(self, key):

        ''' Delete an item from service state.

            :param key:
            :returns: '''

        if key in self.state['service']:
            del self.state['service'][key]

    def __setitem__(self, key, value):

        ''' `service[key] = value` syntax to set
            an item in service state.

            :param key:
            :param value:
            :returns: '''

        self._setstate(key, value)

    def __getitem__(self, key):

        ''' `var = service[key]` syntax to get
            an item from service state.

            :param key:
            :returns: '''

        return self._getstate(key, None)

    def __delitem__(self, key):

        ''' `del service[key] syntax` to delete
            an item from service state.

            :param key:
            :returns: '''

        self._delstate(key)


class ProxiedStructure(abc.ABCMeta):

    ''' Metaclass for property-gather-enabled classes. '''

    def __new__(cls, name, chain, mappings):

        ''' Read mapped properties, store on the
            object, along with a reverse mapping.

            :param name:
            :param chain:
            :param mappings:
            :returns: '''

        if name == 'ProxiedStructure':
            return type(name, chain, mappings)

        # Init calculated data attributes
        mappings['_pmap'] = {}
        mappings['_plookup'] = []

        # Define __contains__ proxy
        def _contains(proxied_o, flag_or_value):

            ''' Bidirectionally-compatible __contains__
                replacement.

                :param proxied_o:
                :param flag_or_value:
                :returns: '''

            return flag_or_value in proxied_o._plookup

        # Define __getitem__ proxy
        def _getitem(proxied_o, fragment):

            ''' Attempt to resolve the fragment by a
                forward, then reverse resolution chain.

                :param proxied_o:
                :param fragment:
                :returns: '''

            if proxied_o.__contains__(fragment):
                return proxied_o._pmap.get(fragment)

        # Define __setitem__ proxy
        def _setitem(proxied_o, n, v):

            ''' Block setitem calls, because this is a
                complicated object that is supposed
                to be a modelling tool only.

                :param proxied_o:
                :param n:
                :param v:
                :raises NotImplementedError: '''

            raise NotImplementedError('Not implemented')

        # Map properties into data and lookup attributes
        map(lambda x: [mappings['_pmap'].update(dict(x)), mappings['_plookup'].append([x[0][0], x[1][0]])],
            (((attr, value), (value, attr)) for attr, value in mappings.items() if not attr.startswith('_')))

        if '__getitem__' not in mappings:
            mappings['__getitem__'] = _getitem
        if '__setitem__' not in mappings:
            mappings['__setitem__'] = _setitem
        if '__contains__' not in mappings:
            mappings['__contains__'] = _contains

        return super(cls, cls).__new__(cls, name, chain, mappings)


class BidirectionalEnum(object):

    ''' Small and simple datastructure for mapping
        static flags to smaller values. '''

    __singleton__ = True
    __metaclass__ = ProxiedStructure

    @classmethod
    def reverse_resolve(cls, code):

        ''' Resolve a mapping, by it's integer/string code.

            :param code:
            :returns: '''

        if code in cls._pmap:
            return cls._pmap[code]
        return False

    @classmethod
    def forward_resolve(cls, flag):

        ''' Resolve a mapping, by it's string property name.

            :param flag:
            :returns: '''

        if flag in cls._pmap:
            return cls.__getattr__(flag)
        return False

    @classmethod
    def resolve(cls, flag): return cls.forward_resolve(flag)

    @classmethod
    def __serialize__(cls):

        ''' Flatten down into a structure suitable for
            storage/transport.

            :returns: '''

        return dict([(k, v) for k, v in dir(cls) if not k.startswith('_')])

    @classmethod
    def __json__(cls):

        ''' Flatten down and serialize into JSON.

            :returns: '''

        return cls.__serialize__()

    @classmethod
    def __repr__(cls):

        ''' Display a string representation of
            a flattened self.

            :returns: '''

        return '::'.join([
            "<%s" % self.__class__.__name__,
            ','.join([
                block for block in ('='.join([str(k), str(v)]) for k, v in cls.__serialize__().items())]),
            "BiDirectional>"
            ])


class TrackedDictionary(object):

    ''' Keeps track of modifications and
        modified state for a dictionary. '''

    __metaclass__ = abc.ABCMeta

    __data = {}
    __seen = set([])
    __dirty = None
    __target = None
    __failfast = False
    __mutations = []

    def __init__(self, initial={}, target=None):

        ''' Prepare internal data storage.

            :param initial:
            :param target:
            :returns: '''

        self.__data, self.__dirty, self.__seen, self.__target, self.__mutations = initial, None, set([]), target, []

    def __getitem__(self, key, exception=KeyError):

        ''' Retrieve from internal storage.

            :param key:
            :param exception:
            :raises KeyError:
            :raises AttributeError:
            :raises Exception:
            :returns: '''

        value = self.__data.get(key, _EMPTY)
        if value == _EMPTY:
            if self.__failfast:
                raise exception("TrackedDictionary could not resolve key '%s'." % key)
        return value

    def __setitem__(self, key, value):

        ''' Set a value in internal storage.

            :param key:
            :param value:
            :returns: '''

        self.__dirty = True
        self.__data[key] = value
        self.__seen.add(key)
        self.__mutations.append((key, value))

    def __delitem__(self, key, exception=KeyError):

        ''' Remove an item from internal storage.

            :param key:
            :param exception:
            :raises KeyError:
            :raises AttributeError:
            :raises Exception:
            :returns: '''

        if key in self:
            self.__mutations.append((key, _TOMBSTONE))
            del self.__data[key]
            self.__dirty = True
            return
        raise exception("TrackedDictionary could not delete missing key '%s'." % key)

    def __nonzero__(self):

        ''' Indicates whether this dictionary is empty or not.

            :returns: '''

        return True if self._data else False

    def __contains__(self, key):

        ''' Indicate whether we have a key or not.

            :param key:
            :returns: '''

        return key in self.__seen

    def __len__(self):

        ''' Return the length of this TrackedDictionary.

            :returns: '''

        return len(self.__data)

    def __repr__(self):

        ''' Properly allow serialization.

            :returns: '''

        return self.__data.__repr__()

    def __iter__(self):

        ''' Iterate over keys in internal storage.

            :returns: '''

        for k in self.__data.iterkeys():
            yield k

    def __json__(self):

        ''' JSON hook.

            :returns: '''

        return self.__data

    @classmethod
    def __subclasshook__(cls, other):

        ''' Check if the provided object is a TrackedDictionary.

            :param other:
            :raises NotImplementedError:
            :returns: '''

        if cls is TrackedDictionary:
            if any("reconcile" in i.__dict__ for i in other.__mro__):
                return True
        return NotImplementedError('Not implemented.')

    @abc.abstractmethod
    def reconcile(self, target=None):

        ''' Flatten this object's mutation pool onto the target object.

            :param target:
            :raises NotImplementedError: '''

        raise NotImplementedError('Not implemented.')

    def dirty(self):

        ''' Return this object's `dirty` status.

            :returns: '''

        return self.__dirty

    def mutations(self):

        ''' Return this object's mutation pool.

            :returns: '''

        return self.__mutations[:]

    def update(self, mapping):

        ''' Update internal values.

            :param mapping:
            :returns: '''

        if isinstance(mapping, list):
            mapping = dict(mapping)
        for k, v in mapping.items():
            self.__setitem__(k, v)
        return self.__data

    def items(self):

        ''' Return a list of (keys, values).

            :returns: '''

        return self.__data.items()

    def keys(self):

        ''' Return a list of all available keys.

            :returns: '''

        return self.__data.keys()

    def values(self):

        ''' Return a list of all available values.

            :returns: '''

        return self.__data.values()

    def iteritems(self):

        ''' Yield (keys, values) one at a time.

            :returns: '''

        for k, v in self.__data.iteritems():
            yield k, v

    def iterkeys(self):

        ''' Yield keys one at a time.

            :returns: '''

        for k in self.__data.iterkeys():
            yield k

    def itervalues(self):

        ''' Yield values one at a time.

            :returns: '''

        for v in self.__data.itervalues():
            yield v

    def get(self, key, default=None):

        ''' Retrieve an item, safely, optionally returning
            `default` if no item could be found.

            :param key:
            :param default:
            :returns: '''

        if self.__contains__(key):
            return self.__data.get(key, default)
        return default

    __setattr__ = __setitem__
    __getattr__ = lambda x, y: x.__getitem__(y)


class PropertyDescriptor(object):

    ''' Utility class used to encapsulate a name, type,
        and set of options for a property on a data model. '''

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

        ''' Set this property's internal value.

            :param instance:
            :param value:
            :raises ValueError:
            :returns: '''

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

        ''' Get this property's internal value.

            :param instance:
            :param owner:
            :returns: '''

        # if empty, return None
        if self.__value == _EMPTY:
            if hasattr(instance, '__sentinel__'):
                if instance.__sentinel__:
                    return _EMPTY
            return None
        else:
            return self.__value

    def __delete__(self, instance):

        ''' Delete this property's internal value.

            :param instance:
            :returns: '''

        # set value to empty
        self.__value = _EMPTY
