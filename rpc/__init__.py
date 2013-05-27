# -*- coding: utf-8 -*-

"""
------------------------
apptools2: service layer
------------------------

the ``apptools service layer`` is a componentized subsystem
built on top of *Google ProtoRPC* and integrated with the
rest of the apptools platform.

classes in this package let you specify structured RPC
services, and load/unload/configure/dispatch them in a
convenient, integrated way.

:author: Sam Gammon (sam@momentum.io)
:copyright: (c) 2013 momentum labs.
:license: This is private source code - Ampush has been granted an
          unlimited, exclusive license for embedded use. For details
          about embedded licenses and other legalese, see `LICENSE.md`.
"""

# stdlib
import os
import time
import base64
import hashlib
import inspect
import logging

# apptools
from apptools import api
from apptools import core
from apptools import util
from apptools import model

# apptools util
from apptools.util import json
from apptools.util import debug
from apptools.util import platform
from apptools.util import decorators
from apptools.util import datastructures


#### ==== Integration Imports ==== ####


## App Config
try:
    import config
    _DEBUG = config.debug  # allow debug override but default to ``True`
except:
    _DEBUG, config = True, False

## AppFactory
try:
    import appfactory
except:
    appfactory = False
    if _DEBUG:
        logging.debug('Service layer failed to find `appfactory`.')

## Google Cloud Endpoints
try:
    import endpoints
except:
    endpoints = False
    if _DEBUG:
        logging.debug('Service layer failed to find `endpoints`.')


#### ==== Dependencies ==== ####
try:
    import protorpc

    # remote / message packages
    from protorpc import remote
    from protorpc.remote import method as proto_method
    from protorpc.remote import Service as ProtoService

    # message packages
    from protorpc import messages as pmessages
    from protorpc.messages import Field as ProtoField
    from protorpc.messages import Message as ProtoMessage

    # message types
    from protorpc import message_types as pmessage_types
    from protorpc.message_types import VoidMessage as ProtoVoidMessage

    # WSGI handlers
    from protorpc import wsgi
    from protorpc.wsgi import service as gateway

except:

    #
    # The apptools service layer requires ProtoRPC to function.
    #

    logging.warning('ProtoRPC could not be found - service layer not available.')

else:

    #### ==== Constants ==== ####

    # pull system config
    srvconfig = {}
    if config:
        srvconfig = config.config.get('apptools.services', {})

    # setup defaults for module-level constants
    _DEFAULT_GETPARAM = 'rq'
    _DEFAULT_BASEPATH = '/_api'
    _DEFAULT_REGISTRY_PATH = _DEFAULT_BASEPATH + '/registry'
    _DEFAULT_OAUTH_SCOPES = ("https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile")
    _DEFAULT_OAUTH_AUDIENCES = (endpoints.API_EXPLORER_CLIENT_ID,) if endpoints else '292824132082.apps.googleusercontent.com'

    # allow override of above constants via config
    if config and len(srvconfig):
        http = srvconfig.get('http', {})
        oauth = srvconfig.get('oauth', {})
        registry = srvconfig.get('registry', {})

        # copy in HTTP config, if any
        if len(http):
            _DEFAULT_BASEPATH = http.get('base', _DEFAULT_BASEPATH)
            _DEFAULT_GETPARAM = http.get('request_param', _DEFAULT_GETPARAM)

        # copy in oauth config, if any
        if len(oauth):
            _DEFAULT_OAUTH_SCOPES = oauth.get('defaults', {}).get('scopes', _DEFAULT_OAUTH_SCOPES)
            _DEFAULT_OAUTH_AUDIENCES = oauth.get('defaults', {}).get('audiences', _DEFAULT_OAUTH_AUDIENCES)

        # copy in registry config, if any
        if len(registry):
            _DEFAULT_REGISTRY_PATH = registry.get('path', _DEFAULT_REGISTRY_PATH)


    #### ==== Message Fields ==== ####

    ## VariantField - a hack that allows a fully-variant field in ProtoRPC message classes.
    class VariantField(ProtoField):

        ''' Field definition for a completely variant field. '''

        VARIANTS = frozenset([pmessages.Variant.DOUBLE, pmessages.Variant.FLOAT, pmessages.Variant.BOOL,
                              pmessages.Variant.INT64, pmessages.Variant.UINT64, pmessages.Variant.SINT64,
                              pmessages.Variant.INT32, pmessages.Variant.UINT32, pmessages.Variant.SINT32,
                              pmessages.Variant.STRING, pmessages.Variant.MESSAGE, pmessages.Variant.BYTES, pmessages.Variant.ENUM])

        DEFAULT_VARIANT = pmessages.Variant.STRING

        type = (int, long, bool, basestring, dict, pmessages.Message)


    #### ==== Message Classes ==== ####

    ## Key - valid as a request or a response, specifies an apptools model key.
    class Key(ProtoMessage):

        ''' Message for a :py:class:`apptools.model.Key`. '''

        encoded = pmessages.StringField(1)  # encoded (`urlsafe`) key
        kind = pmessages.StringField(2)  # kind name for key
        id = pmessages.IntegerField(3)  # integer ID for key
        name = pmessages.StringField(4)  # string name for key
        namespace = pmessages.StringField(5)  # string namespace for key
        parent = pmessages.MessageField('Key', 6)  # recursive key message for parent


    ## Echo - valid as a request as a response, simply defaults to 'Hello, world!'. Mainly for testing.
    class Echo(ProtoMessage):

        ''' I am rubber and you are glue... '''

        message = pmessages.StringField(1, default='Hello, world!')


    ## expose message classes alias
    messages = datastructures.DictProxy(**{

        # apptools-provided messages
        'Key': Key,  # message class for an apptools model key
        'Echo': Echo,  # echo message defaulting to `hello, world` for testing

        # builtin messages
        'Message': ProtoMessage,  # top-level protorpc message class
        'VoidMessage': ProtoVoidMessage,  # top-level protorpc void message

        # specific types
        'Enum': pmessages.Enum,  # enum descriptor / definition class
        'Field': pmessages.Field,  # top-level protorpc field class
        'FieldList': pmessages.FieldList,  # top-level protorpc field list class

        # field types
        'VariantField': VariantField,  # generic hold-anything property (may cause serializer problems - be careful)
        'BooleanField': pmessages.BooleanField,  # boolean true/false field
        'BytesField': pmessages.BytesField,  # low-level binary-safe string field
        'EnumField': pmessages.EnumField,  # field for referencing an :py:class:`pmessages.Enum` class
        'FloatField': pmessages.FloatField,  # field for a floating point number
        'IntegerField': pmessages.IntegerField,  # field for an integer
        'MessageField': pmessages.MessageField,  # field for a sub-message (:py:class:`pmessages.Message`)
        'StringField': pmessages.StringField  # field for unicode or ASCII strings

    })

    # detect newest version of protorpc
    if hasattr(pmessage_types, 'DateTimeField'):
        messages['DateTimeField'] = pmessage_types.DateTimeField
    elif _DEBUG:
        # notify the user in debug mode that `datetime` support will get crappy
        logging.warning('Detected out-of-date `ProtoRPC` library. Failed to load `datetime` support.')
        logging.debug('Python `datetime` values will be converted to dumb `isoformat`.')

    #### ==== Service Classes ==== ####

    ## RemoteServiceFactory - class for generating/preparing new RemoteService objects
    class RemoteServiceFactory(object):

        ''' Responsible for manufacturing BaseService classes. '''

        @classmethod
        def new(self, service):

            ''' Return the service, unmodified (this will be used later).

                :param service: Service class to initialize. Must be a
                                descendent of :py:class:`remote.Service`.

                :returns: Constructed / materialized descendent of
                          :py:class:`remote.Service`. '''

            return service


    ## Service - top-level base class for remote service classes.
    @platform.PlatformInjector
    class Service(ProtoService):

        ''' Top-level parent class for ProtoRPC-based apptools services. '''

        # == Public Properties == #
        name = None
        version = None
        enabled = True

        # == Internal Properties == #
        _version = (0, 5)
        _config_path = 'apptools.rpc.Service'

        # Encapsulator references
        handler = None
        request = {}
        middleware = {}

        # Mapped exceptions
        exceptions = datastructures.DictProxy({
            'ApplicationError': remote.ApplicationError
        })

        # Jinja2 integration
        context = {}
        context_injectors = []

        @decorators.memoize
        @decorators.classproperty
        def config(cls):

            ''' Resolve :py:class:`Service`-specific config.

                :returns: Configuration ``dict`` for the current
                          :py:class:`Service` class, if any. '''

            return srvconfig or {}

        @decorators.memoize
        @decorators.classproperty
        def logging(cls):

            ''' Generate a dedicated logging pipe.

                :returns: An instance of :py:class:`debug.AppToolsLogger`,
                          customized for the current :py:class:`Service`
                          class. '''

            _psplit = cls._config_path.split('.')
            return debug.AppToolsLogger(**{
                'path': '.'.join(_psplit[0:-1]),
                'name': _psplit[-1]})._setcondition(cls.config.get('debug', True))

        def initialize_request_state(self, state):

            ''' Request state hook from ``ProtoRPC``.

                :param state: State object handed in from ``ProtoRPC``,
                              which should be a descendent of the class
                              :py:class:`protorpc.remote.RequestState`. '''

            pass


