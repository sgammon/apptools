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
import base64
import config
import hashlib
import webapp2

# ProtoRPC imports
from protorpc import remote
from protorpc import messages as pmessages
from protorpc import message_types as pmessage_types

# Service handlers
from protorpc.webapp import service_handlers
from protorpc.webapp.service_handlers import RequestError

# Extras import
from webapp2_extras import protorpc as proto

# Util Imports
from apptools.util import json
from apptools.util import platform
from apptools.util import _loadModule

# Datastructure Imports
from apptools.util import debug
from apptools.util import datastructures

# Field Imports
from apptools.services import fields as afields
from apptools.services import decorators as adecorators

# Decorator Imports
from apptools.services.decorators import audit
from apptools.services.decorators import caching
from apptools.services.decorators import security

# Globals
decorate = adecorators
_global_debug = config.debug
logging = debug.AppToolsLogger('apptools.services', 'ServiceLayer')

# Service layer middleware object cache
_middleware_cache = {}


#+#+#+ ==== Handy Message Classes ==== +#+#+#

## KeyMessage
# Represents an NDB/LDB datastore key for a stored entity.
class KeyMessage(pmessages.Message):

    ''' Represents a datastore key. '''

    encoded = pmessages.StringField(1)
    kind = pmessages.StringField(2)
    id = pmessages.IntegerField(3)
    name = pmessages.StringField(4)
    namespace = pmessages.StringField(5)


#+#+#+ ==== System API Messages ==== +#+#+#

## Echo
# Valid as a request or response. Defaults `message` to "Hello, World!". Mainly for testing purposes.
class Echo(pmessages.Message):

    ''' I am rubber and you are glue... '''

    message = pmessages.StringField(1, default='Hello, World!')


## Service flags
# Decorate remote methods with these flags to annotate them with specific policies/functionality.
flags = datastructures.DictProxy({

    ''' Shortcut to remote method/service decorator flags. '''

    # Decorators related to logging/backend output
    'audit': datastructures.DictProxy({
        'monitor': audit.Monitor,
        'debug': audit.Debug,
        'loglevel': audit.LogLevel,
    }),

    # Decorators related to caching, for performance
    'caching': datastructures.DictProxy({
        'local': caching.LocalCacheable,
        'memcache': caching.MemCacheable,
        'cacheable': caching.Cacheable,
    }),

    # Decorators related to access & security
    'security': datastructures.DictProxy({
        'authorize': security.Authorize,
        'authenticate': security.Authenticate,
        'admin': security.AdminOnly
    })

})

## Message Classes
# A nice, universal mapping to all available ProtoRPC message field types.
messages = datastructures.DictProxy({

    ''' Shortcut to all available message classes. '''

    # AppTools-provided classes
    'Echo': Echo,
    'KeyMessage': KeyMessage,

    # Builtin messages
    'Message': pmessages.Message,
    'VoidMessage': pmessage_types.VoidMessage,

    # Specific types
    'Enum': pmessages.Enum,
    'Field': pmessages.Field,
    'FieldList': pmessages.FieldList,

    # Field shortcuts
    'VariantField': afields.VariantField,
    'BooleanField': pmessages.BooleanField,
    'BytesField': pmessages.BytesField,
    'EnumField': pmessages.EnumField,
    'FloatField': pmessages.FloatField,
    'IntegerField': pmessages.IntegerField,
    'MessageField': pmessages.MessageField,
    'StringField': pmessages.StringField

})


## RemoteServiceFactory
# Class for generating/preparing new RemoteService objects
class RemoteServiceFactory(object):

    ''' Responsible for manufacturing BaseService classes. '''

    @classmethod
    def new(self, service):

        ''' Return the service, unmodified (this will be used later). '''

        return service


## BaseService
# Top-level base class for remote services classes.
@platform.PlatformInjector
class BaseService(remote.Service, datastructures.StateManager):

    ''' Top-level parent class for ProtoRPC-based API services. '''

    # General stuff
    handler = None
    request = datastructures.DictProxy({})
    middleware = {}

    # Template stuff
    context = {}
    context_injectors = []

    # Service state
    state = {
        'request': {},
        'opts': {},
        'service': {}
    }

    # Service config
    config = {
        'global': {},
        'module': {},
        'service': {}
    }

    def __init__(self, *args, **kwargs):

        ''' Pass init up the chain. '''

        super(BaseService, self).__init__(*args, **kwargs)

    @webapp2.cached_property
    def logging(self):

        ''' Create and return a logging channel. '''

        global logging
        return logging.extend(path='apptools.services.ServiceLayer.RemoteService', name=self.__class__.__name__)

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

    def initialize_request_state(self, state):

        ''' Copy over request state from ProtoRPC. '''

        self.state['request'] = state
        super(BaseService, self).initialize_request_state(state)

    def _initializeRemoteService(self):

        ''' Internal method for initializing a service and injecting its config. '''

        # Copy over global, module, and service configuration
        self.config['global'] = self._globalServicesConfig

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

    def prepare_followup(self, task=None, pipeline=None, start=False, queue_name=None, idempotence_key='', *args, **kwargs):

        ''' Prepare and set a followup task or pipeline, for async functionality. '''

        global _global_debug

        result_return = []
        if self._servicesConfig.get('debug', False):
            self.logging.debug('Loading remote method followup.')
            self.logging.debug('Task: "' + str(task) + '".')
            self.logging.debug('Pipeline: "' + str(pipeline) + '".')
            self.logging.debug('Start: "' + str(start) + '".')
            self.logging.debug('Args: "' + str(args) + '".')
            self.logging.debug('Kwargs: "' + str(kwargs) + '".')

        if task is not None:

            if self._servicesConfig.get('debug', False):
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

            if self._servicesConfig.get('debug', False):
                self.logging.debug('Instantiated task: "%s".' % t)

            if start:
                if self._servicesConfig.get('debug', False):
                    self.logging.debug('Starting followup task.')
                if queue_name is not None:
                    self.logging.debug('Adding to queue "%s".' % queue_name)
                    self._setstate('followup', t.add(queue_name=queue_name))
                else:
                    self._setstate('followup', t.add())
                if self._serviceConfig.get('debug', False):
                    self.logging.info('Resulting task: "%s".' % t)
                self.setflag('tid', str(t))

            result_return.append(t)

        if pipeline is not None:

            if self._servicesConfig.get('debug', False):
                self.logging.debug('Loading followup pipeline.')

            kwargs['async_config'] = {
                'token': self._getstate('token'),
                'channel': self._getstate('channel'),
                'rid': self._getstate('rid'),
                'rhash': self._getstate('rhash'),
                'rmodel': '.'.join(self._getstate('rmodel').__module__.split('.') + [self._getstate('rmodel').__class__.__name__])
            }

            p = pipeline(*args, **kwargs)
            if self._servicesConfig.get('debug', False):
                self.logging.debug('Instantiated pipeline: "%s".' % p)

            if start:
                if self._servicesConfig.get('debug', False):
                    self.logging.debug('Starting followup pipeline.')
                if queue_name is not None:
                    self._setstate('followup', p.start(queue_name=queue_name, idempotence_key=idempotence_key))
                else:
                    self._setstate('followup', p.start(idempotence_key=idempotence_key))

            if self._servicesConfig.get('debug', False):
                self.logging.info('Resulting pipeline: "%s".' % p)
            self.setflag('pid', str(p.pipeline_id))

            result_return.append(p)

        return tuple(result_return)


## RemoteServiceHandler
# This class is responsible for bridging a request to a remote service class, dispatching/executing to get the response, and returning it to the client.
@platform.PlatformInjector
class RemoteServiceHandler(service_handlers.ServiceHandler, datastructures.StateManager):

    ''' Handler for responding to remote API requests. '''

    # Request/Response Containers
    state = {}
    service = None
    interpreted_body = None
    enable_async_mode = False

    _request_envelope = datastructures.DictProxy({

        'id': None,
        'opts': {},
        'agent': {}

    })

    _response_envelope = datastructures.DictProxy({

        'id': None,
        'flags': {},
        'status': 'success'

    })

    # Exception Mappings
    ApplicationError = remote.ApplicationError

    @webapp2.cached_property
    def logging(self):

        ''' Log channel shim. '''

        global logging
        return logging.extend(name='RemoteServiceHandler')

    # Log Management
    def log(self, message):

        ''' Logging shortcut. '''

        if self._servicesConfig['logging'] is True:
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

        middleware = self._servicesConfig.get('middleware', False)
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

        sdebug = self._servicesConfig.get('debug', False)
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

        sdebug = self._servicesConfig.get('debug', False)
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
            from google.appengine.ext.ndb import key as nkey

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

        self.response.headers['X-Content-Type-Options'] = 'nosniff'
        content_type = self._ServiceHandler__get_content_type()

        # Copy handler to service
        self.service.handler = self

        # Provide server state to the service.  If the service object does not have
        # an "initialize_request_state" method, will not attempt to assign state.
        state_initializer = self.service.initialize_request_state
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

        self.service.request = self.request
        self.service.response = self.response
        self.service.state['request'] = request_state

        # Check for initialize hook
        if hasattr(self.service, 'initialize'):
            self.service.initialize()

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

            except (RequestError, pmessages.DecodeError), err:
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

            if hasattr(self.service, 'after_request_hook'):
                self.service.after_request_hook()

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
@platform.PlatformInjector
class RemoteServiceHandlerFactory(proto.ServiceHandlerFactory):

    ''' Factory for preparing ServiceHandlers. '''

    @webapp2.cached_property
    def logging(self):

        ''' Log channel shim. '''

        global logging
        return logging.extend(name='RemoteServiceHandlerFactory')

    @webapp2.cached_property
    def installed_mappers(self):

        ''' Return installed mappers, calculated from config. '''

        global _global_debug

        # Decide whether we should output logs
        if self._servicesConfig.get('debug', False) is True:
            output_debug = True
        else:
            output_debug = False

        mappers = []
        for mapper in self._globalServicesConfig.get('mappers', []):
            if mapper.get('enabled', False) is not True:
                if output_debug:
                    self.logging.info('Mapper at name "' + str(mapper.get('name', 'UnknownMapper')) + '" skipped according to config.')
                continue

            try:
                mapper_cls = _loadModule(tuple(['.'.join(mapper.get('path').split('.')[0:-1]), mapper.get('path').split('.')[-1]]))
                mapper = mapper_cls()

            except ImportError:
                self.logging.warning('Invalid path to RPCMapper of name "%s". Given path: "%s" does not exist or otherwise could not be imported.' % (str(mapper.get('name', 'UnknownMapper')), str(mapper.get('path', 'UnknownPath'))))
                if _global_debug:
                    raise
                else:
                    continue

            except Exception, e:
                self.logging.error('Unknown exception encountered when trying to install the RPC mapper at name "%s" with path "%s". Exception: "%s".' % (str(mapper.get('name', 'UnknownMapper')), str(mapper.get('path', 'UnknownPath')), str(e)))
                if _global_debug:
                    raise
                else:
                    continue

            else:
                mappers.append(mapper)

        if (output_debug or _global_debug) and len(mappers) == 0:
            self.logging.warning(' === NO VALID RPCMAPPERS FOUND. ===')

        return mappers

    def log(self, message):

        ''' Logging shortcut. '''

        if self._servicesConfig['logging'] is True:
            if config.debug:
                self.logging.info(str(message))
            else:
                self.logging.debug(str(message))
        return

    def error(self, message):

        ''' Error shortcut. '''

        self.logging.error('ServiceHandlerFactory ERROR: ' + str(message))

    @classmethod
    def default(cls, service_factory, parameter_prefix=''):

        ''' Prepare the default setup for a service, including the appropriate RPC mappers. This is where we inject our custom JSONRPC mapper. '''

        ## Create Service
        factory = cls(service_factory)

        ## Add request mappers
        for mapper in factory.installed_mappers:
            factory.add_request_mapper(mapper)

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
        middleware = self._servicesConfig.get('middleware', False)
        if middleware is not False and len(middleware) > 0:

            for name, cfg in middleware:
                self.log('Considering ' + str(name) + ' middleware...')
                if cfg['enabled'] is True:
                    try:
                        if name not in _middleware_cache or config.debug:
                            middleware_class = webapp2.import_string(cfg['path'])
                        else:
                            middleware_class = _middleware_cache[name]

                        middleware_object = middleware_class(debug=cfg['debug'], config=self._servicesConfig, opts=cfg.get('args', {}))
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
