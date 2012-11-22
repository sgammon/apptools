# -*- coding: utf-8 -*-

'''

AppTools Util

Holds small utilities and useful pieces of code/functionality that don't
belong anywhere more-specific in AppTools.

-sam (<sam@momentum.io>)

'''

## Base Imports
import os
import config
import logging as std_logging

## Export Util Controllers
from apptools.util.debug import AppToolsLogger

## Exported Datastructures
from apptools.util.datastructures import DictProxy
from apptools.util.datastructures import UtilStruct
from apptools.util.datastructures import ObjectProxy
from apptools.util.datastructures import CallbackProxy

## Resolve JSON support
try:
    import json as std_json
except ImportError:
    try:
        import simplejson as sjson
    except ImportError:
        try:
            from django.utils import json as djson
        except ImportError:
            std_logging.critical('No valid JSON adapter found. This could cause serious problems...')
            if config.debug:
                raise
        else:
            libjson = djson  # apparently, simplejson is NOT installed and we're running on py < 2.7, on appengine (probably)
    else:
        libjson = sjson  # apparently, simplejson is installed and we're running on py < 2.7
else:
    libjson = std_json  # we're running on >= py 2.7. life is gewd

## Globals
_MODULE_LOADER_CACHE = {}
_MODULE_LOADER_SENTINEL = type(os)

logging = AppToolsLogger('apptools.util')


## _loadAPIModule
# Take an entry from one of the package bridges, and lazy-load it into _MODULE_LOADER_CACHE.
def _loadModule(entry):

    ''' Callback to lazy-load an API module in tuple(path, item) format. '''

    global _MODULE_LOADER_CACHE

    if entry not in _MODULE_LOADER_CACHE:

        # tuple syntax - ('path.to.module', 'ModuleOrClassName')
        if isinstance(entry, tuple):
            path, name = entry
            mod = __import__(path, globals(), locals(), [name])
            _MODULE_LOADER_CACHE[entry] = getattr(mod, name)

        # string syntax - "path.to.module.ModuleOrClassName"
        elif isinstance(entry, basestring):
            mod = __import__(entry, globals(), locals(), ['*'])
            _MODULE_LOADER_CACHE[entry] = mod

        # module syntax - you're kind of an idiot.
        elif isinstance(entry, _MODULE_LOADER_SENTINEL):
            return module

        else:
            logging.error('Lazyloader failed to resolve module for shortcut: "' + str(entry) + '".')
            raise ImportError("Could not resolve module for entry '" + str(entry) + "'.")

    return _MODULE_LOADER_CACHE[entry]

## Custom JSON Encoder/Decoder
class AppToolsJSONEncoder(libjson.JSONEncoder):

    ''' Custom encoder that implements the __json__ method interface. '''

    def default(self, target):

        ''' Invoked when the JSON encoder can't encode something. '''

        if hasattr(target, '__json__'):
            return libjson.JSONEncoder.default(target)

## Splice in custom JSON codec
class JSONWrapper(object):

    ''' Utility wrapper for json.dumps/loads that proxies to AppTools' custom JSON codec. '''

    JSONDecoder = libjson.JSONDecoder
    JSONEncoder = libjson.JSONEncoder

    scanner = libjson.scanner
    _default_decoder = libjson._default_decoder
    _default_encoder = libjson._default_encoder

    @classmethod
    def dump(cls, iterator):

        ''' Streaming serialization to JSON strings. '''

        for i in interator:
            yield AppToolsJSONEncoder().encode(i)

    @classmethod
    def load(cls, iterator):

        ''' Streaming deserialization from JSON strings. '''

        for i in iterator:
            yield jsonlib.loads(i)

    @classmethod
    def dumps(cls, struct):

        ''' Dump a structure to a JSON string. '''

        return AppToolsJSONEncoder().encode(struct)

    @classmethod
    def loads(cls, string):

        ''' Load via libjson. '''

        return libjson.loads(string)

json = JSONWrapper

__all__ = [UtilStruct, DictProxy, ObjectProxy, CallbackProxy, AppToolsLogger, json, JSONWrapper, AppToolsJSONEncoder]
