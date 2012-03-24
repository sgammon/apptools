# -*- coding: utf-8 -*-

## Export Util Controllers
from apptools.util.debug import AppToolsLogger
from apptools.util.debug import AppToolsLogController

## Exported Datastructures
from apptools.util.datastructures import UtilStruct
from apptools.util.datastructures import DictProxy
from apptools.util.datastructures import ObjectProxy
from apptools.util.datastructures import CallbackProxy

## Resolve JSON support
try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        from django.utils import json

logging = AppToolsLogController('apptools.util')

_api_cache = {}


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
