# -*- coding: utf-8 -*-

'''

Util: Datastructures

Holds useful classes and code for managing/manipulating/using specialized datastructures.

-sam (<sam@momentum.io>)

'''

import logging


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
        if name in self._entries:
            return self.callback(self._entries.get(name))
        else:
            raise KeyError

    def __getattr__(self, name):
        return self.callback(self._entries.get(name))


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