# -*- coding: utf-8 -*-

'''

AppTools Util

Holds small utilities and useful pieces of code/functionality that don't
belong anywhere more-specific in AppTools.

-sam (<sam@momentum.io>)

'''

## Base Imports
import config
import logging as std_logging

## Export Util Controllers
from apptools.util.debug import AppToolsLogger

## Exported Datastructures
from apptools.util.datastructures import UtilStruct
from apptools.util.datastructures import DictProxy
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
            json = djson  # apparently, simplejson is NOT installed and we're running on py < 2.7, on appengine (probably)
    else:
        json = sjson  # apparently, simplejson is installed and we're running on py < 2.7
else:
    json = std_json  # we're running on >= py 2.7. life is gewd


## Globals
_api_cache = {}
logging = AppToolsLogger('apptools.util')


## _loadAPIModule
# Take an entry from one of the package bridges, and lazy-load it into _api_cache.
def _loadModule(entry):

    ''' Callback to lazy-load an API module in tuple(path, item) format. '''

    global _api_cache

    if entry not in _api_cache:
        if isinstance(entry, tuple):
            path, name = entry
            mod = __import__(path, globals(), locals(), [name])
            _api_cache[entry] = getattr(mod, name)
        elif isinstance(entry, basestring):
            mod = __import__(entry, globals(), locals(), ['*'])
            _api_cache[entry] = mod
        else:
            logging.error('Lazyloader failed to resolve module for shortcut: "' + str(entry) + '".')
            raise ImportError("Could not resolve module for entry '" + str(entry) + "'.")

    return _api_cache[entry]

__all__ = [UtilStruct, DictProxy, ObjectProxy, CallbackProxy, AppToolsLogger, json]
