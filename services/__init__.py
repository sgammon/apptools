# -*- coding: utf-8 -*-

'''

AppTools Service Layer

This module governs the creation, management, and dispatch of ProtoRPC-backed API services.
Everything from dispatch, to serialization, to logging/caching/security is taken care of for you -
this module is very configurable using the "config/services.py" file.

-sam (<sam@momentum.io>)

'''

# Basic Imports
import time
import hmac
import base64
import config
import hashlib
import webapp2
import datetime

# ProtoRPC imports
from protorpc import remote
from protorpc import messages
from protorpc import protojson
from protorpc import message_types

# Message imports
from protorpc.messages import Field
from protorpc.messages import Variant

# Service handlers
from protorpc.webapp import service_handlers
from protorpc.webapp.service_handlers import RequestError

# Extras import
from webapp2_extras import protorpc as proto

# Util Imports
from apptools.util import json
from apptools.util import platform
from apptools.util.debug import AppToolsLogger

# Datastructure Imports
from apptools.util.datastructures import DictProxy

# Decorator Imports
from apptools.services.decorators import audit
from apptools.services.decorators import caching
from apptools.services.decorators import security

# New NDB Import
from google.appengine.ext.ndb import key as nkey


# Globals
_global_debug = config.debug
logging = AppToolsLogger('apptools.services', 'ServiceLayer')
date_time_types = (datetime.datetime, datetime.date, datetime.time)

# Service layer middleware object cache
_middleware_cache = {}


## Service flags
# Decorate remote methods with these flags to annotate them with specific policies/functionality.
flags = DictProxy({

    # Decorators related to logging/backend output
    'audit': DictProxy({
        'monitor': audit.Monitor,
        'debug': audit.Debug,
        'loglevel': audit.LogLevel,
    }),

    # Decorators related to caching, for performance
    'caching': DictProxy({
        'local': caching.LocalCacheable,
        'memcache': caching.MemCacheable,
        'cacheable': caching.Cacheable,
    }),

    # Decorators related to access & security
    'security': DictProxy({
        'authorize': security.Authorize,
        'authenticate': security.Authenticate,
        'admin': security.AdminOnly
    })

})


## VariantField
# A hack that allows a fully-variant field in ProtoRPC message classes.
class VariantField(Field):

    ''' Field definition for a completely variant field. '''

    VARIANTS = frozenset([Variant.DOUBLE, Variant.FLOAT, Variant.BOOL,
                          Variant.INT64, Variant.UINT64, Variant.SINT64,
                          Variant.INT32, Variant.UINT32, Variant.SINT32,
                          Variant.STRING, Variant.MESSAGE, Variant.BYTES, Variant.ENUM])

    DEFAULT_VARIANT = Variant.STRING

    type = (int, long, bool, basestring, dict, messages.Message)

## Message Fields
# A nice, universal mapping to all available ProtoRPC message field types.
fields = DictProxy({

    ''' Shortcut to all the available message fields. '''

    'Variant': VariantField,
    'Boolean': messages.BooleanField,
    'Bytes': messages.BytesField,
    'Enum': messages.EnumField,
    'Float': messages.FloatField,
    'Integer': messages.IntegerField,
    'Message': messages.MessageField,
    'String': messages.StringField

})


## Custom JSON encoder
# This class overrides an internal ProtoRPC class so that we can properly package/unpackage API requests according to apptools' **wire format**.
class _MessageJSONEncoder(protojson._MessageJSONEncoder):

    ''' Custom JSON encoder for API request & response messages. '''

    indent = None
    encoding = 'utf-8'
    sort_keys = True
    allow_nan = True
    ensure_ascii = True
    check_circular = True
    skipkeys = True
    use_decimal = False

    current_indent_level = 0

    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def default(self, value):

        ''' Overrides JSONEncoder's default() method. '''

        if isinstance(value, messages.Enum):
            return str(value)

        if isinstance(value, messages.Message):
            result = {}
            for field in value.all_fields():
                item = value.get_assigned_value(field.name)
                if item not in (None, [], ()):
                    result[field.name] = self.jsonForValue(item)
                    if isinstance(item, list):  # for repeated values...
                        listvalue = [self.jsonForValue(x) for x in item]
                        result[field.name] = listvalue

            else:
                return super(_MessageJSONEncoder, self).default(value)

        elif isinstance(value, AppJSONRPCMapper.GenericResponse):
            result = {}
            for k, v in value.to_dict().items():
                if v not in (None, [], ()):
                    if isinstance(v, list):
                        listvalue = [self.jsonForValue(x) for x in v]
                        result[k] = listvalue
                    else:
                        result[k] = self.jsonForValue(v)
                else:
                    result[k] = super(_MessageJSONEncoder, self).default(v)
        else:
            return super(_MessageJSONEncoder, self).default(value)

        return result

    def jsonForValue(self, value):

        ''' Return JSON for a given Python value. '''

        if isinstance(value, (basestring, int, float, bool)):
            return value

        elif isinstance(value, date_time_types):
            return str(value)

        elif isinstance(value, messages.Message):
            for item in value.all_fields():
                self.jsonForValue(item)

        else:
            return str(value)


## AppJSONRPCMapper
# Custom RPC mapper that properly unpacks JSONRPC requests according to apptools' **wire format**.
class AppJSONRPCMapper(service_handlers.JSONRPCMapper):

    ''' Custom JSONRPC Mapper for managing JSON API requests. '''

    handler = None
    _request = {

        'id': None,
        'opts': {},
        'agent': {}

    }

    def __init__(self):
        super(AppJSONRPCMapper, self).__init__()

    @webapp2.cached_property
    def ServicesConfig(self):

        ''' Return the project services config. '''

        return config.config.get('apptools.project.services')

    def encode_request(self, struct):

        ''' Encode a request. '''

        encoded = _MessageJSONEncoder().encode(struct)
        return encoded

    def build_response(self, handler, response, response_envelope=None, extra_response_content={}):

        ''' Encode a response. '''

        self.handler = handler
        try:
            if isinstance(response, messages.Message):
                response.check_initialized()
            else:
                response = self.GenericResponse.from_struct(response)
            if response_envelope is not None and handler is None:
                envelope = self.envelope(response_envelope, response)
                if extra_response_content is not None and isinstance(extra_response_content, dict):
                    for k, v in extra_response_content.items():
                        if k not in envelope['response']:
                            envelope['response'][k] = v
                encoded_response = _MessageJSONEncoder().encode(envelope)
                return encoded_response
            else:
                envelope = _MessageJSONEncoder().encode(self.envelope(handler._response_envelope, response))

        except messages.ValidationError, err:
            raise service_handlers.RequestError('Unable to encode message: %s' % err)
        else:
            if handler is not None:  # so we can inject responses...
                handler.response.headers['Content-Type'] = "application/json"
                handler.response.write(envelope)
            return envelope

    def envelope(self, wrap, response):

        ''' Wrap the result of the request in a descriptive, helpful envelope. '''

        sysconfig = config.config.get('apptools.project')
        svsconfig = config.config.get('apptools.project.services')

        ## Compile signature
        signature = [
            svsconfig.get('secret_key', self.ServicesConfig.get('secret_key', '__development__')),  # HMAC key
            str(response),  # message
            svsconfig.get('hmac_hash', hashlib.md5)
        ]

        ## Start building response
        response_envelope = {

            'id': wrap.get('id'),
            'status': wrap.get('status'),
            'response': {},
            'flags': wrap.get('flags'),
            'platform': {
                'name': config.config.get('apptools.project').get('name', 'AppTools'),
                'version': '.'.join(map(lambda x: str(x), [sysconfig['version']['major'], sysconfig['version']['minor'], sysconfig['version']['micro']]))
            }

        }

        ## Add debug info
        if config.debug or self.ServicesConfig.get('debug', False):
            response_envelope['platform']['debug'] = config.debug
            response_envelope['platform']['build'] = sysconfig['version']['build']
            response_envelope['platform']['release'] = sysconfig['version']['release']
            response_envelope['platform']['engine'] = 'AppTools/ProtoRPC'

            if self.ServicesConfig.get('debug', False):
                response_envelope['platform']['info'] = {

                    'datacenter': self.handler.request.environ.get('DATACENTER'),
                    'instance': self.handler.request.environ.get('INSTANCE_ID'),
                    'request_id': self.handler.request.environ.get('REQUEST_ID_HASH'),
                    'server': self.handler.request.environ.get('SERVER_SOFTWARE'),
                    'runtime': self.handler.request.environ.get('APPENGINE_RUNTIME'),
                    'multithread': self.handler.request.environ.get('wsgi.multithread'),
                    'multiprocess': self.handler.request.environ.get('wsgi.multiprocess')

                }
                if self.api.backends.get_backend() is not None:
                    response_envelope['platform']['info']['layer'] = 'backend'
                    response_envelope['platform']['info']['instance'] = self.api.backends.get_instance()
                else:
                    response_envelope['platform']['info']['layer'] = 'frontend'

        ## Add actual response
        response_envelope['response'] = {

            'type': str(response.__class__.__name__),
            'content': response,
            'signature': hmac.new(*signature).hexdigest()

        }

        ## Done!
        return response_envelope

    def decode_request(self, message_type, dictionary):

        ''' Decode a request. '''

        def decode_dictionary(message_type, dictionary):

            ''' Decode a dictionary of items (recursive). '''

            message = message_type()
            if isinstance(dictionary, dict):
                for key, value in dictionary.iteritems():
                    if value is None:
                        message.reset(key)
                    continue

                    try:
                        field = message.field_by_name(key)
                    except KeyError:
                        # TODO(rafek): Support saving unknown values.
                        continue

                    # Normalize values in to a list.
                    if isinstance(value, list):
                        if not value:
                            continue
                        else:
                            value = [value]

                        valid_value = []
                        for item in value:
                            if isinstance(field, messages.EnumField):
                                item = field.type(item)
                            elif isinstance(field, messages.BytesField):
                                item = base64.b64decode(item)
                            elif isinstance(field, messages.MessageField):
                                item = decode_dictionary(field.type, item)
                            elif (isinstance(field, messages.FloatField) and
                                    isinstance(item, (int, long))):
                                item = float(item)
                            valid_value.append(item)

                    if field.repeated:
                        getattr(message, field.name)
                        setattr(message, field.name, valid_value)
                    else:
                        setattr(message, field.name, valid_value[-1])
            return message

        message = message_type()
        if isinstance(dictionary, list):
            return message
        elif isinstance(dictionary, dict):
            for key, value in dictionary.iteritems():
                if value is None:
                    message.reset(key)
                    continue

                try:
                    field = message.field_by_name(key)
                except KeyError:
                    # TODO(rafek): Support saving unknown values.
                    continue

                # Normalize values in to a list.
                if isinstance(value, list):
                    if not value:
                        continue
                else:
                    value = [value]

                valid_value = []
                for item in value:
                    if isinstance(field, messages.EnumField):
                        item = field.type(item)
                    elif isinstance(field, messages.BytesField):
                        item = base64.b64decode(item)
                    elif isinstance(field, messages.MessageField):
                        item = decode_dictionary(field.type, item)
                    elif (isinstance(field, messages.FloatField) and
                            isinstance(item, (int, long))):
                        item = float(item)
                    valid_value.append(item)

                if field.repeated:
                    getattr(message, field.name)
                    setattr(message, field.name, valid_value)
                else:
                    setattr(message, field.name, valid_value[-1])

        return message

    def build_request(self, handler, request_type):

        ''' Build a request object. '''

        try:
            if hasattr(handler, 'interpreted_body') and handler.interpreted_body is not None:
                request_object = handler.interpreted_body
            else:
                request_object = protojson._load_json_module().loads(handler.request.body)

            try:
                request_id = request_object['id']
                request_agent = request_object['agent']
                request_body = request_object['request']
                request_opts = request_object['opts']
            except AttributeError:
                raise service_handlers.RequestError('Request is missing a valid ID, agent, request opts or request body.')

            self._request['id'] = request_id
            self._request['agent'] = request_agent
            self._request['opts'] = request_opts

            handler._request_envelope['id'] = self._request['id']
            handler._request_envelope['opts'] = self._request['opts']
            handler._request_envelope['agent'] = self._request['agent']

            handler._response_envelope['id'] = self._request['id']

            logging.info('Decoding request...')

            return self.decode_request(request_type, request_body['params'])

        except (messages.ValidationError, messages.DecodeError), err:
            raise service_handlers.RequestError('Unable to parse request content: %s' % err)


# Class for generating/preparing new RemoteService objects
class RemoteServiceFactory(object):

    @classmethod
    def new(self, service):
        return service


## BaseService
# Top-level base class for remote services classes.
@platform.PlatformInjector
class BaseService(remote.Service):

    ''' Top-level parent class for ProtoRPC-based API services. '''

    # General stuff
    handler = None
    request = DictProxy({})
    middleware = {}

    # State + config
    state = {
        'request': {},
        'opts': {},
        'service': {}
    }

    config = {
        'global': {},
        'module': {},
        'service': {}
    }

    @webapp2.cached_property
    def logging(self):

        ''' Create and return a logging channel. '''

        global logging
        return logging.extend(path='apptools.services.ServiceLayer.RemoteService', name=self.__class__.__name__)

    @webapp2.cached_property
    def globalConfig(self):

        ''' Cached shortcut to services config. '''

        return config.config.get('apptools.services')

    @webapp2.cached_property
    def serviceConfig(self):

        ''' Cached shortcut to project services config. '''

        return config.config.get('apptools.project.services')

    def __init__(self, *args, **kwargs):

        ''' Pass init up the chain. '''

        super(BaseService, self).__init__(*args, **kwargs)

    def initiate_request_state(self, state):

        ''' Copy over request state from ProtoRPC. '''

        super(BaseService, self).initiate_request_state(state)

    def _initializeRemoteService(self):

        ''' Internal method for initializing a service and injecting it's config. '''

        # Copy over global, module, and service configuration
        self.config['global'] = self.globalConfig

        if hasattr(self, 'moduleConfigPath'):
            self.config['module'] = config.config.get(getattr(self, 'moduleConfigPath', '__null__'), {})

            # If we have a module + service config path, pull it from the module's branch
            if hasattr(self, 'configPath'):
                path = getattr(self, 'configPath').split('.')
                if len(path) > 0:
                    fragment = self.config['module']
                    for i in xrange(0, len(path) - 1):
                        if path[i] in fragment:
                            fragment = fragment[path[i]]
                    if isinstance(fragment, dict):
                        self.config['service'] = fragment

        # No module configuration
        else:
            # Copy over default module config
            self.config['module'] = self.config['global']['defaults']['module']

            # If we have a service config path but no module config path...
            if hasattr(self, 'configPath'):
                # Try importing it as a top-level namespace
                toplevel = config.config.get(self.configPath, None)
                if toplevel is None:
                    # If that doesn't work, copy it over from defaults...
                    self.config['service'] = self.config['global']['defaults']['service']
                else:
                    self.config['service'] = toplevel

            else:
                # If we have nothing, copy over defaults...
                self.config['service'] = self.config['global']['defaults']['service']

        # Check for initialize hook
        if hasattr(self, 'initialize'):
            self.initialize()

    def _setstate(self, key, value):

        ''' Set an item in service state. '''

        self.state['service'][key] = value

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

    def __repr__(self):

        ''' Cleaner string representation. '''

        return '<RemoteService::' + '.'.join(self.__module__.split('.') + [self.__class__.__name__]) + '>'

    def setflag(self, name, value):

        ''' Set a flag to be returned in the response envelope. '''

        if self.handler is not None:
            return self.handler.setflag(name, value)

    def getflag(self, name):

        ''' Get the value of a flag set to be returned in the response envelope. '''

        if self.handler is not None:
            return self.handler.getflag(name)

    def set_response(self, response):

        ''' Add the response message model to the internal service state, so it can be passed to a followup task. This gives the task proper context and allows the task to push a regular response asynchronously. '''

        self._setstate('rmodel', response)
        return

    def prepare_followup(self, task=None, pipeline=None, start=False, queue_name=None, idempotence_key='', *args, **kwargs):

        ''' Prepare and set a followup task or pipeline, for async functionality. '''

        global _global_debug

        result_return = []
        if self.servicesConfig.get('debug', False):
            self.logging.debug('Loading remote method followup.')
            self.logging.debug('Task: "' + str(task) + '".')
            self.logging.debug('Pipeline: "' + str(pipeline) + '".')
            self.logging.debug('Start: "' + str(start) + '".')
            self.logging.debug('Args: "' + str(args) + '".')
            self.logging.debug('Kwargs: "' + str(kwargs) + '".')

        if task is not None:

            if self.servicesConfig.get('debug', False):
                self.logging.debug('Loading followup task.')

            if 'params' not in kwargs:
                kwargs['params'] = {}

            kwargs['params']['_token'] = self._getstate('token')
            kwargs['params']['_channel'] = self._getstate('channel')
            kwargs['params']['_rhash'] = self._getstate('rhash')
            kwargs['params']['_rhash'] = self._getstate('rid')
            kwargs['params']['_rmodel'] = '.'.join(self._getstate('rmodel').__module__.split('.') + [self._getstate('rmodel').__class__.__name__])

            if _global_debug:
                self.logging.dev('Injected token "%s", channel "%s", rhash "%s" and model path "%s".' % (self._getstate('token'), self._getstate('channel'), self._getstate('rhash'), kwargs['params']['_rmodel']))

            t = task(*args, **kwargs)

            if self.servicesConfig.get('debug', False):
                self.logging.debug('Instantiated task: "%s".' % t)

            if start:
                if self.servicesConfig.get('debug', False):
                    self.logging.debug('Starting followup task.')
                if queue_name is not None:
                    self.logging.debug('Adding to queue "%s".' % queue_name)
                    self._setstate('followup', t.add(queue_name=queue_name))
                else:
                    self._setstate('followup', t.add())
                if self.servicesConfig.get('debug', False):
                    self.logging.info('Resulting task: "%s".' % t)
                self.setflag('tid', str(t))

            result_return.append(t)

        if pipeline is not None:

            if self.servicesConfig.get('debug', False):
                self.logging.debug('Loading followup pipeline.')

            kwargs['async_config'] = {
                'token': self._getstate('token'),
                'channel': self._getstate('channel'),
                'rid': self._getstate('rid'),
                'rhash': self._getstate('rhash'),
                'rmodel': '.'.join(self._getstate('rmodel').__module__.split('.') + [self._getstate('rmodel').__class__.__name__])
            }

            p = pipeline(*args, **kwargs)
            if self.servicesConfig.get('debug', False):
                self.logging.debug('Instantiated pipeline: "%s".' % p)

            if start:
                if self.servicesConfig.get('debug', False):
                    self.logging.debug('Starting followup pipeline.')
                if queue_name is not None:
                    self._setstate('followup', p.start(queue_name=queue_name, idempotence_key=idempotence_key))
                else:
                    self._setstate('followup', p.start(idempotence_key=idempotence_key))

            if self.servicesConfig.get('debug', False):
                self.logging.info('Resulting pipeline: "%s".' % p)
            self.setflag('pid', str(p.pipeline_id))

            result_return.append(p)

        return tuple(result_return)

    def set_followup(self, tid=None, pid=None):

        ''' Manually set the TID and/or PID response header. '''

        if tid is None:
            self.setflag('tid', str(tid))
        if pid is None:
            self.setflag('pid', str(pid))
        return

    def go_async(self):

        ''' Go into async mode. '''

        return self.handler.go_async()

    def can_async(self):

        ''' Check if async mode is possible. '''

        return self.handler.can_async()

    def get_request_body(self):

        ''' Interpret the request body and cache it for later. '''

        return self.handler.get_request_body()


## RemoteServiceHandler
# This class is responsible for bridging a request to a remote service class, dispatching/executing to get the response, and returning it to the client.
class RemoteServiceHandler(service_handlers.ServiceHandler):

    ''' Handler for responding to remote API requests. '''

    # Request/Response Containers
    state = {}
    service = None
    interpreted_body = None
    enable_async_mode = False

    _request_envelope = DictProxy({

        'id': None,
        'opts': {},
        'agent': {}

    })

    _response_envelope = DictProxy({

        'id': None,
        'flags': {},
        'status': 'success'

    })

    # Exception Mappings
    ApplicationError = remote.ApplicationError

    # Config
    @webapp2.cached_property
    def servicesConfig(self):

        ''' Cached shortcut to services config. '''

        return config.config.get('apptools.services')

    @webapp2.cached_property
    def logging(self):

        ''' Log channel shim. '''

        global logging
        return logging.extend(name='RemoteServiceHandler')

    # Log Management
    def log(self, message):

        ''' Logging shortcut. '''

        if self.servicesConfig['logging'] is True:
            if config.debug:
                self.logging.info(str(message))
            else:
                self.logging.debug(str(message))
        return

    def error(self, message):

        ''' Error shortcut. '''

        self.logging.error(str(message))
        return

    # Response Flags
    def setflag(self, name, value):

        ''' Set a flag for the response envelope, like whether the response is cached or fresh. '''

        self._response_envelope['flags'][name] = value
        return

    def getflag(self, name):

        ''' Retrieve the current value of an envelope flag. '''

        if name in self._response_envelope['flags']:
            return self._response_envelope['flags'][name]
        else:
            return None

    def getflags(self):

        ''' Retrieve all envelope flags. '''

        return self._response_envelope['flags']

    # Envelope Access
    def setstatus(self, status):

        ''' Set the status of a response. Good choices would be things like 'success' and 'error'. '''

        self._response_envelope['status'] = status
        return

    def getstatus(self):

        ''' Get the response's current status. '''

        return self._response_envelope['status']

    def setid(self, id):

        ''' Set the ID of the response you're sending. '''

        self._response_envelope['id'] = id
        return

    def getid(self):

        ''' Get the current ID of the response you're sending. '''

        return self._response_envelope['id']

    # Middleware
    def run_post_action_middleware(self, service):

        ''' Run middleware that has a hook to run _after_ a request has been fulfilled by the RemoteService class. '''

        global global_debug
        global _middleware_cache

        middleware = self.servicesConfig.get('middleware', False)
        if middleware is not False and len(middleware) > 0:

            for name, middleware_object in service.middleware.items():
                self.log('Considering ' + str(name) + ' middleware...')
                try:

                    if hasattr(middleware_object, 'after_request'):
                        middleware_object.after_request(self.service, self.request, self.response)
                        continue
                    else:
                        self.log('Middleware ' + str(name) + ' does not have after_request method. Continuing.')
                        continue

                except Exception, e:
                    self.error('Middleware "' + str(name) + '" raised an unhandled exception of type "' + str(e) + '".')
                    if config.debug:
                        raise
                    continue

        else:
            self.log('Middleware is none or 0.')

    def go_async(self):

        ''' Indicate that a response will be delivered via Channel API. '''

        self.setflag('alt', 'socket')
        self.setflag('token', self.state['token'])
        self.setflag('rhash', self.state['rhash'])
        self.setstatus('wait')

        self.service._setstate('token', self.state['token'])
        self.service._setstate('channel', self.state['channel'])
        self.service._setstate('rid', self._request_envelope.id)
        self.service._setstate('rhash', self.state['rhash'])

        self.enable_async_mode = True

        return True, self.state['token'], self.state['channel'], self.state['rhash']

    def get_request_body(self):

        ''' Interpret the request body early, so it can be manipulated/read. '''

        if hasattr(self, 'interpreted_body') and self.interpreted_body is not None:
            return self.interpreted_body
        else:
            try:
                self.interpreted_body = json.loads(self.request.body)
            except Exception:
                self.interpreted_body = None
                return False
            else:
                return self.interpreted_body

    def can_async(self):

        ''' Check and return whether an async response is possible. '''

        sdebug = self.servicesConfig.get('debug', False)
        if sdebug:
            self.logging.info('--- Beginning check for async compatibility.')

        if 'alt' in self._request_envelope.opts:

            if sdebug:
                self.logging.debug('1. `alt` flag found. value: "' + str(self._request_envelope.opts['alt']) + '".')

            if self._request_envelope.opts['alt'] == 'socket':

                if 'token' in self._request_envelope.opts:

                    if sdebug:
                        self.logging.debug('2. `token` flag found. value: "' + str(self._request_envelope.opts['token']) + '".')

                    if self._request_envelope.opts['token'] not in set(['', '_null_']):

                        if sdebug:
                            self.logging.debug('3. `token` is not null or invalid. proceeding.')

                        channel_token = self._get_channel_from_token(self._request_envelope.opts['token'])

                        if sdebug:
                            self.logging.debug('4. pulled `channel_token`: "' + str(channel_token) + '".')

                        if channel_token is not False:
                            if sdebug:
                                self.logging.debug('ASYNC CAPABLE! :)')

                            self.state['token'] = self._request_envelope.opts['token']
                            self.state['channel'] = channel_token
                            self.state['rhash'] = base64.b64encode(self.state['channel'] + str(self._request_envelope['id']))
                            return True
                        else:
                            self.logging.warning('Could not pull channel ID.')

                            self.setflag('alt', 'denied')
                            self.setflag('pushcmd', 'reconnect')
                            return False
        return False

    def _get_channel_from_token(self, token):

        ''' Resolve a channel ID/seed from the client's token. '''

        sdebug = self.servicesConfig.get('debug', False)
        if sdebug:
            self.logging.info('Getting channel ID from token "' + str(token) + '".')

        ## try memcache first
        token_key = self._get_token_key(token)
        if sdebug:
            self.logging.info('Token key calculated: "' + str(token_key) + '".')

        channel_id = self.api.memcache.get(token_key)
        if channel_id is None:

            if sdebug:
                self.logging.warning('Channel ID not found in memcache.')

            ## try datastore if we can't find it in memcache
            from apptools.model.builtin import PushSession

            ups = nkey.Key(PushSession, token_key).get()
            if ups is not None:

                if sdebug:
                    self.logging.info('PushSession found in datastore. Found seed "' + str(ups.seed) + '".')

                ## if the model's found, set it in memecache
                self.api.memcache.set(token_key, {'seed': ups.seed, 'key': ups.key.urlsafe()})
                return ups.seed
            else:
                self.logging.error('PushSession not found in datastore. Invalid or discarded seed.')
                return False
        else:
            if sdebug:
                self.logging.info('Channel ID found in memcache. Returning!')
            return channel_id['seed']

    def _get_token_key(self, token):

        ''' Encode and prefix a channel token, suitable for use as a key in memcache/megastore. '''

        return 'push_token::' + base64.b64encode(hashlib.sha256(token).hexdigest())

    def handle(self, http_method, service_path, remote_method):

        ''' Handle a remote service request. '''

        self.response.headers['x-content-type-options'] = 'nosniff'
        content_type = self._ServiceHandler__get_content_type()

        # Provide server state to the service.  If the service object does not have
        # an "initialize_request_state" method, will not attempt to assign state.
        try:
            state_initializer = self.service.initialize_request_state
        except AttributeError:
            pass
        else:
            server_port = self.request.environ.get('SERVER_PORT', None)
            if server_port:
                server_port = int(server_port)

                request_state = remote.HttpRequestState(
                    remote_host=self.request.environ.get('REMOTE_HOST', None),
                    remote_address=self.request.environ.get('REMOTE_ADDR', None),
                    server_host=self.request.environ.get('SERVER_HOST', None),
                    server_port=server_port,
                    http_method=http_method,
                    service_path=service_path,
                    headers=list(self._ServiceHandler__headers(content_type)))
            state_initializer(request_state)

        if not content_type:
            self.setstatus('fail')
            self.__send_simple_error(400, 'Invalid RPC request: missing content-type')
            return

        # Search for mapper to mediate request.
        for mapper in self._ServiceHandler__factory.all_request_mappers():
            if content_type in mapper.content_types:
                break
        else:
            self.setstatus('fail')
            self._ServiceHandler__send_simple_error(415, 'Unsupported content-type: %s' % content_type)
            return

        try:
            if http_method not in mapper.http_methods:
                self.setstatus('fail')
                self._ServiceHandler__send_simple_error(405, 'Unsupported HTTP method: %s' % http_method)
                return

            try:
                try:
                    method = getattr(self.service, remote_method)
                    method_info = method.remote
                except AttributeError, err:
                    self.setstatus('fail')
                    self._ServiceHandler__send_error(400, remote.RpcState.METHOD_NOT_FOUND_ERROR, 'Unrecognized RPC method: %s' % remote_method, mapper)
                    return

                request = mapper.build_request(self, method_info.request_type)

            except (RequestError, messages.DecodeError), err:
                self.setstatus('fail')
                self._ServiceHandler__send_error(400, remote.RpcState.REQUEST_ERROR, 'Error parsing RPC request (%s)' % err, mapper)
                return

            try:
                response = method(request)
            except self.ApplicationError, err:
                self.setstatus('fail')
                self._ServiceHandler__send_error(400, remote.RpcState.APPLICATION_ERROR, err.message, mapper, err.error_name)
                return

            mapper.build_response(self, response)

        except Exception, err:
            self.setstatus('fail')
            self.logging.error('An unexpected error occured when handling RPC: %s' % err, exc_info=1)
            self.logging.exception('Unexpected service exception of type "%s": "%s".' % (type(err), str(err)))
            self._ServiceHandler__send_error(500, remote.RpcState.SERVER_ERROR, 'Internal Server Error', mapper)
            if config.debug:
                raise
            else:
                return

    # Remote method execution
    def dispatch(self, factory, service):

        ''' Dispatch the remote request, and generate a response. '''

        # Unfortunately we need to access the protected attributes.
        self._ServiceHandler__factory = factory
        self._ServiceHandler__service = service

        # Link the service and handler both ways so we can pass stuff back and forth
        service.handler = self
        self.service = service

        request = self.request
        service.request = request

        request_method = request.method
        method = getattr(self, request_method.lower(), None)

        service_path, remote_method = request.route_args

        if method:
            self.handle(request_method, service_path, remote_method)
            self.run_post_action_middleware(service)
        else:
            message = 'Unsupported HTTP method: %s' % request_method
            logging.error(message)
            self.response.status = '405 %s' % message

        if request_method == 'GET':
            status = self.response.status_int
            if status in (405, 415) or not request.content_type:
                # Again, now a protected method.
                self._ServiceHandler__show_info(service_path, remote_method)


## RemoteServiceHandlerFactory
# Over here, we're responsible for creating and preparing remote service handlers, which dispatch a request to a service class.
class RemoteServiceHandlerFactory(proto.ServiceHandlerFactory):

    ''' Factory for preparing ServiceHandlers. '''

    @webapp2.cached_property
    def servicesConfig(self):

        ''' Cached access to services config. '''

        return config.config.get('apptools.services')

    @webapp2.cached_property
    def logging(self):

        ''' Log channel shim. '''

        global logging
        return logging.extend(name='RemoteServiceHandlerFactory')

    def log(self, message):

        ''' Logging shortcut. '''

        if self.servicesConfig['logging'] is True:
            if config.debug:
                self.logging.info(str(message))
            else:
                logging.debug(str(message))
        return

    def error(self, message):

        ''' Error shortcut. '''

        self.logging.error('ServiceHandlerFactory ERROR: ' + str(message))

    @classmethod
    def default(cls, service_factory, parameter_prefix=''):

        ''' Prepare the default setup for a service, including the appropriate RPC mappers. This is where we inject our custom JSONRPC mapper. '''

        factory = cls(service_factory)

        # our nifty mapper, for correctly interpreting & providing our envelope schema
        factory.add_request_mapper(AppJSONRPCMapper())

        factory.add_request_mapper(service_handlers.ProtobufRPCMapper())
        factory.add_request_mapper(service_handlers.URLEncodedRPCMapper())

        return factory

    def __call__(self, request, remote_path, remote_method):

        ''' Handle a remote service call. '''

        global _middleware_cache

        # Extract response
        request.clock = {}
        request.clock['threadstart'] = time.time()
        response = request.response

        # Manufacture service + handler
        service = self.service_factory()
        service._initializeRemoteService()

        # Consider service middleware
        middleware = self.servicesConfig.get('middleware', False)
        if middleware is not False and len(middleware) > 0:

            for name, cfg in middleware:
                self.log('Considering ' + str(name) + ' middleware...')
                if cfg['enabled'] is True:
                    try:
                        if name not in _middleware_cache or config.debug:
                            middleware_class = webapp2.import_string(cfg['path'])
                        else:
                            middleware_class = _middleware_cache[name]

                        middleware_object = middleware_class(debug=cfg['debug'], config=self.servicesConfig, opts=cfg.get('args', {}))
                        service.middleware[name] = middleware_object

                        if hasattr(middleware_object, 'before_request'):
                            service, request, response = middleware_object.before_request(service, request, response)
                            continue
                        else:
                            self.log('Middleware ' + str(name) + ' does not have pre_request method. Continuing.')
                            continue

                    except Exception, e:
                        self.error('Middleware "' + str(name) + '" raise an unhandled exception of type "' + str(e) + '".')
                        if config.debug:
                            raise
                        else:
                            continue

                else:
                    self.log('Middleware ' + str(name) + ' is disabled.')
                    continue
        else:
            self.log('Middleware was none or 0.')

        service_handler = RemoteServiceFactory.new(RemoteServiceHandler(self, service))
        service_handler.request = request
        service_handler.response = response

        self.log('Handler prepared. Dispatching...')

        service_handler.dispatch(self, service)
