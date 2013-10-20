# -*- coding: utf-8 -*-

'''

    apptools util

    holds small utilities and useful pieces of code/functionality that don't
    belong anywhere specific.

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


## Base Imports
import os
import datetime
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
            std_logging.critical('No valid JSON adapter found. '
                                 'This could cause serious problems...')
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


def _loadModule(entry):

    ''' Callback to lazy-load an API module in tuple(path, item) format.

        :param entry:
        :raise ValueError:
        :raise ImportError:
        :returns: '''

    global _MODULE_LOADER_CACHE

    if not entry:
        raise ValueError("Invalid module spec: '%s'." % entry)

    if entry not in _MODULE_LOADER_CACHE:

        # tuple syntax - ('path.to.module', 'ModuleOrClassName')
        if isinstance(entry, tuple):
            path, name = entry
            mod = __import__(path, globals(), locals(), [name])
            _MODULE_LOADER_CACHE[entry] = getattr(mod, name)
            return _MODULE_LOADER_CACHE[entry]

        # string syntax - "path.to.module.ModuleOrClassName"
        elif isinstance(entry, basestring):
            mod = __import__(entry, globals(), locals(), ['*'])
            _MODULE_LOADER_CACHE[entry] = mod
            return _MODULE_LOADER_CACHE[entry]

        # module syntax - you're kind of an idiot.
        elif isinstance(entry, _MODULE_LOADER_SENTINEL):
            return entry

        logging.error('Lazyloader failed to resolve module for shortcut: "' + str(entry) + '".')
        raise ImportError("Could not resolve module for entry '" + str(entry) + "'.")

    return _MODULE_LOADER_CACHE[entry]


class AppToolsJSONEncoder(libjson.JSONEncoder):

    ''' Custom encoder that implements the __json__ method interface. '''

    def __init__(self, *args, **kwargs):

        ''' Initialize this JSONEncoder.

            :param args:
            :param kwargs:
            :returns: '''

        # pass up the chain
        super(AppToolsJSONEncoder, self).__init__(*args, **kwargs)

    def default(self, target):

        ''' Invoked when the JSON encoder can't encode something.

            :param target:
            :raises ImportError:
            :returns: '''

        if hasattr(target, '__json__'):
            return libjson.JSONEncoder.default(target)
        try:
            from jinja2 import runtime
        except ImportError as e:
            pass
        else:
            if isinstance(target, runtime.Undefined):
                return None
        try:
            from apptools import model
        except ImportError as e:
            raise
        else:
            if isinstance(target, model.Key):
                return target.urlsafe()
            if isinstance(target, model.Model):
                return target.to_json()

        if isinstance(target, (datetime.datetime, datetime.date, datetime.time)):
            return target.isoformat()
        if _NDB:
            if isinstance(target, ndb.Key):
                return target.urlsafe()
            if isinstance(target, ndb.Model):
                return target.to_dict()
            if isinstance(target, datastore_types.BlobKey):
                return str(target)
        return libjson.JSONEncoder.default(self, target)


class JSONWrapper(object):

    ''' Utility wrapper for json.dumps/loads that proxies
        to AppTools' custom JSON codec. '''

    JSONDecoder = libjson.JSONDecoder
    JSONEncoder = libjson.JSONEncoder

    scanner = libjson.scanner
    _default_decoder = libjson._default_decoder
    _default_encoder = libjson._default_encoder

    @classmethod
    def dump(cls, iterator, **kwargs):

        ''' Streaming serialization to JSON strings.

            :param iterator:
            :param kwargs:
            :returns: '''

        for i in interator:
            yield AppToolsJSONEncoder(**kwargs).encode(i)

    @classmethod
    def load(cls, iterator, **kwargs):

        ''' Streaming deserialization from JSON strings.

            :param iterator:
            :param kwargs:
            :returns: '''

        for i in iterator:
            yield jsonlib.loads(i, **kwargs)

    @classmethod
    def dumps(cls, struct, **kwargs):

        ''' Dump a structure to a JSON string.

            :param struct:
            :param kwargs:
            :returns: '''

        return AppToolsJSONEncoder(**kwargs).encode(struct)

    @classmethod
    def loads(cls, string, **kwargs):

        ''' Load via libjson.

            :param string:
            :param kwargs:
            :returns: '''

        return libjson.loads(string, **kwargs)

json = JSONWrapper

__all__ = [UtilStruct, DictProxy, ObjectProxy, CallbackProxy, AppToolsLogger, json, JSONWrapper, AppToolsJSONEncoder]
