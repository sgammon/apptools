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
    from protorpc.remote import method
    from protorpc.remote import Service

    # message packages
    from protorpc import messages as pmessages
    from protorpc.messages import Field as ProtoField
    from protorpc.messages import Message as ProtoMessage

    # message types
    from protorpc import message_types as pmessage_types
    from protorpc.message_types import VoidMessage as ProtoVoidMessage

    # WSGI handlers
    from protorpc import wsgi
    from protorpc.wsgi import service_mappings

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
    _DEFAULT_OAUTH_AUDIENCES = (endpoints.API_EXPLORER_CLIENT_ID,) if endpoints else None

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
        'Key': Key,
        'Echo': Echo,

        # builtin messages
        'Message': ProtoMessage,
        'VoidMessage': ProtoVoidMessage,

    })
