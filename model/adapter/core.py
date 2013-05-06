# -*- coding: utf-8 -*-

'''

    apptools2: core model adapters
    -------------------------------------------------
    |                                               |
    |   `apptools.model.adapter.core`               |
    |                                               |
    |   specifies mixins and adapters that are part |
    |   of the core model adapter distribution.     |
    |                                               |
    -------------------------------------------------
    |   authors:                                    |
    |       -- sam gammon (sam@momentum.io)         |
    -------------------------------------------------
    |   changelog:                                  |
    |       -- apr 1, 2013: initial draft           |
    -------------------------------------------------

'''

# mixin adapters
from abstract import KeyMixin
from abstract import ModelMixin

# apptools util
from apptools.util import json


## DictMixin
# Provides native `to_dict`-type methods to `model.Model` and `model.Key`.
class DictMixin(KeyMixin, ModelMixin):

    ''' Provides `to_dict`-type methods for first-class Model API classes. '''

    def update(self, mapping={}, **kwargs):

        ''' Update properties on this model via a merged dict of mapping + kwargs. '''

        if kwargs: mapping.update(kwargs)
        map(lambda x: setattr(self, x[0], x[1]), mapping.items())
        return self

    def to_dict(self, exclude=tuple(), include=tuple(), filter=None, map=None, _all=False, filter_fn=filter, map_fn=map):

        ''' Export this Entity as a dictionary, excluding/including/filtering/mapping as we go. '''

        dictionary = {}  # return dictionary
        _default_map = False  # flag for default map lambda, so we can exclude only on custom map
        _default_include = False  # flag for including properties unset and explicitly listed in a custom inclusion list

        if not _all: _all = self.__explicit__  # explicit mode implies returning all properties raw

        if not include:
            include = self.__lookup__  # default include list is model properties
            _default_include = True  # mark flag that we used the default

        if not map:
            map = lambda x: x  # substitute no map with a passthrough
            _default_map = True
        
        if not filter: filter = lambda x: True  # substitute no filter with a passthrough

        # freeze our comparison sets
        exclude, include = frozenset(exclude), frozenset(include)

        for name in self.__lookup__:

            # run map fn over (name, value)
            _property_descriptor = self.__class__.__dict__[name]
            name, value = map((name, self._get_value(name, default=self.__class__.__dict__[name]._default)))  # pull with property default

            # run filter fn over (name, vlaue)
            filtered = filter((name, value))
            if not filtered: continue

            # filter out via exclude/include
            if name in exclude:
                continue
            if not _default_include:
                if name not in include: continue

            if value is _property_descriptor._sentinel:  # property is unset
                if not _all and not ((not _default_include) and name in include):  # if it matches an item in a custom include list, and/or we don't want all properties...
                    continue  # skip if all properties not requested
                else:
                    if not self.__explicit__:  # None == sentinel in implicit mode
                        value = None
            dictionary[name] = value        
        return dictionary

    @classmethod
    def to_dict_schema(cls, *args, **kwargs):

        ''' Convert a model or entity's schema to a dictionary, where keys=>values map to properties=>descriptors. '''

        pass


## JSONMixin
# Provides JSON integration to `model.Model` and `model.Key`. 
class JSONMixin(KeyMixin, ModelMixin):

    ''' Provides JSON serialization/deserialization support to `model.Model` and `model.Key`. '''

    def to_json(self, *args, **kwargs):

        ''' Convert an entity to a JSON structure, where keys=>values map to properties=>values. '''

        return json.dumps(self.to_dict(*args, **kwargs))

    @classmethod
    def to_json_schema(cls, *args, **kwargs):

        ''' Convert a model or entity's schema to a dictionary, where keys=>values map to JSON Schema representing properties=>descriptors. '''

        raise NotImplemented()  # @TODO: JSON schema support


# msgpack support
try:
    import msgpack
except ImportError as e:
    pass  # no `msgpack` support :(

else:

    ## MsgpackMixin
    # Provides Msgpack integration to `model.Model` and `model.Key`.
    class MsgpackMixin(KeyMixin, ModelMixin):

        ''' Provides Msgpack serialization/deserialization support to `model.Model` and `model.Key`. '''

        def to_msgpack(cls, *args, **kwargs):

            ''' Convert an entity to a Msgpack structure, where keys=>values map to properties=>values. '''

            pass

        @classmethod
        def to_msgpack_schema(cls, *args, **kwargs):

            ''' Convert a model or entity's schema to a dictionary, where keys=>values map to internal symbols representing properties=>descriptors. '''

            pass
