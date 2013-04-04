# -*- coding: utf-8 -*-

'''

AppTools Service Layer

This module governs the creation, management, and dispatch of ProtoRPC-backed API services.
Everything from dispatch, to serialization, to logging/caching/security is taken care of for you -
this module is very configurable using the "config/services.py" file.

-sam (<sam@momentum.io>)

'''

# Basic Imports
import os
import time
import base64
import config
import hashlib
import inspect
import webapp2

try:
    import endpoints
except ImportError as e:
    endpoints = False

# AppFactory Integration
try:
    import appfactory
except:
    appfactory = False

# ProtoRPC imports
from protorpc import remote
from protorpc import messages as pmessages
from protorpc import message_types as pmessage_types
from protorpc.message_types import VoidMessage

# Service handlers
from protorpc.webapp import service_handlers
from protorpc.webapp.service_handlers import RequestError

# Extras import
from webapp2_extras import protorpc as proto

# AppTools APIs
from apptools.api import BaseObject

# Util Imports
from apptools.util import json
from apptools.util import platform
from apptools.util import _loadModule

# Datastructure Imports
from apptools.util import debug
from apptools.util import datastructures

# Globals
_global_debug = config.debug
logging = debug.AppToolsLogger('apptools.services', 'ServiceLayer')._setcondition(_global_debug)

# Service layer middleware object cache
_middleware_cache = {}
_installed_mappers = []

# OAuth Constants
_DEFAULT_OAUTH_SCOPES = ("https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile")
_DEFAULT_OAUTH_AUDIENCES = (endpoints.API_EXPLORER_CLIENT_ID,) if endpoints else None

#+#+#+ ==== Handy Message Fields ==== +#+#+#

## VariantField
# A hack that allows a fully-variant field in ProtoRPC message classes.
class VariantField(pmessages.Field):

    ''' Field definition for a completely variant field. '''

    VARIANTS = frozenset([pmessages.Variant.DOUBLE, pmessages.Variant.FLOAT, pmessages.Variant.BOOL,
                          pmessages.Variant.INT64, pmessages.Variant.UINT64, pmessages.Variant.SINT64,
                          pmessages.Variant.INT32, pmessages.Variant.UINT32, pmessages.Variant.SINT32,
                          pmessages.Variant.STRING, pmessages.Variant.MESSAGE, pmessages.Variant.BYTES, pmessages.Variant.ENUM])

    DEFAULT_VARIANT = pmessages.Variant.STRING

    type = (int, long, bool, basestring, dict, pmessages.Message)


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
    'VariantField': VariantField,
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
    exceptions = datastructures.DictProxy({

        'ApplicationError': remote.ApplicationError

    })

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


## AbstractPlatformServiceHandler
# Injects abstract root platform mixins, where appripriate.
if appfactory and isinstance(appfactory, type(os)):

    from appfactory import integration

    ## Root Abstract Platform - AppFactory
    class AbstractPlatformServiceHandler(BaseObject, service_handlers.ServiceHandler, integration.AppFactoryMixin):

        ''' Injects AppFactory configuration, shortcut, and state properties. '''

        _appfactory_enabled = True

else:

    ## Vanilla Root Abstract Platform
    class AbstractPlatformServiceHandler(BaseObject, service_handlers.ServiceHandler):

        ''' Used as a base platform service handler when no platform integration is enabled. '''

        _appfactory_enabled = False


## RemoteServiceHandler
# This class is responsible for bridging a request to a remote service class, dispatching/executing to get the response, and returning it to the client.
@platform.PlatformInjector
class RemoteServiceHandler(AbstractPlatformServiceHandler, datastructures.StateManager):

    ''' Handler for responding to remote API requests. '''

    # Request/Response Containers
    state = {}
    uagent = {}
    service = None
    interpreted_body = None
    enable_async_mode = False

    _request_envelope_template = {

        'id': None,
        'opts': {},
        'agent': {}

    }

    _response_envelope_template = {

        'id': None,
        'flags': {},
        'status': 'success'

    }

    # Exception Mappings
    ApplicationError = remote.ApplicationError

    def __init__(self, *args, **kwargs):

        ''' Init - manufactures a new request and response envelope. '''

        self._request_envelope = datastructures.DictProxy(self._request_envelope_template)
        self._response_envelope = datastructures.DictProxy(self._response_envelope_template)

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

    def set_request_body(self, body):

        ''' Set an already-interpreted or raw request body. '''

        if not isinstance(body, basestring):
            self.interpreted_body = body
        else:
            try:
                self.interpreted_body = json.loads(body)
            except Exception:
                self.interpreted_body = None
                return False
            else:
                return self.interpreted_body

    def __send_error(self, http_code, status_state, error_message, mapper, error_name=None):

        ''' Send an error RPC response. '''

        status = remote.RpcStatus(state=status_state, error_message=error_message, error_name=error_name)
        mapper.build_response(self, status)

        self.response.headers['Content-Type'] = mapper.default_content_type
        self.logging.error(error_message)

        response_content = self.response.body
        padding = ' ' * max(0, 512 - len(response_content))

        self.response.write(padding)
        self.response.set_status(http_code, error_message)
        return

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
            self.setstatus('failure')
            self.__send_simple_error(400, 'Invalid RPC request: missing content-type')
            return

        # Search for mapper to mediate request.
        for mapper in self._ServiceHandler__factory.all_request_mappers():
            if content_type in mapper.content_types:
                break
        else:
            self.setstatus('failure')
            self._ServiceHandler__send_simple_error(415, 'Unsupported content-type: %s' % content_type)
            return

        try:
            if http_method not in mapper.http_methods:
                self.setstatus('failure')
                self._ServiceHandler__send_simple_error(405, 'Unsupported HTTP method: %s' % http_method)
                return

            try:
                try:
                    method = getattr(self.service, remote_method)
                    method_info = method.remote
                except AttributeError, err:
                    self.setstatus('failure')
                    self.__send_error(400, remote.RpcState.METHOD_NOT_FOUND_ERROR, 'Unrecognized RPC method: %s' % remote_method, mapper)
                    return

                request = mapper.build_request(self, method_info.request_type)

            except (RequestError, pmessages.DecodeError), err:
                self.setstatus('failure')
                self.__send_error(400, remote.RpcState.REQUEST_ERROR, 'Error parsing RPC request (%s)' % err, mapper)
                return

            if hasattr(self.service, 'before_request_hook'):
                self.service.before_request_hook()

            try:
                response = method(request)
            except self.ApplicationError, err:
                self.setstatus('failure')
                self.__send_error(400, remote.RpcState.APPLICATION_ERROR, err.message, mapper, err.error_name)
                return

            mapper.build_response(self, response)

            baseHeaders = config.config.get('apptools.project.output', {}).get('headers', {})
            for k, v in baseHeaders.items():
                if k.lower() == 'access-control-allow-origin':
                    if v == None:
                        self.response.headers[k] = self.request.headers['origin']
                    else:
                        self.response.headers[k] = v
                else:
                    self.response.headers[k] = v

            if hasattr(self.service, 'after_request_hook'):
                self.service.after_request_hook()

        except Exception, err:
            self.setstatus('failure')
            self.logging.error('An unexpected error occured when handling RPC: %s' % err, exc_info=1)
            self.logging.exception('Unexpected service exception of type "%s": "%s".' % (type(err), str(err)))
            self.__send_error(500, remote.RpcState.SERVER_ERROR, 'Internal Server Error', mapper)
            if config.debug:
                raise
            else:
                return

    # Remote method execution
    def dispatch(self, factory, service):

        ''' Dispatch the remote request, and generate a response. '''

        # Buffer POST body
        self.request.make_body_seekable()

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
    def outputConfig(self):

        ''' Config channel for output config. '''

        return config.config.get('apptools.project.output')

    @webapp2.cached_property
    def installed_mappers(self):

        ''' Return installed mappers, calculated from config. '''

        global _global_debug
        global _installed_mappers

        # Decide whether we should output logs
        if self._servicesConfig.get('debug', False) is True:
            output_debug = True
        else:
            output_debug = False

        if len(_installed_mappers) == 0:
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

            # Set cache
            _installed_mappers = mappers[:]
        else:
            # Read from cache
            mappers = _installed_mappers[:]

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

    def options(self):

        ''' Return a response to an HTTP OPTIONS request, enabling CORS and outputting supported methods. '''

        response = webapp2.Response()
        for k, v in self.outputConfig.get('headers').items():
            if k.lower() == 'access-control-allow-origin':
                if v == None:
                    response.headers[k] = self.request.headers['origin']
                else:
                    response.headers[k] = v
            else:
                response.headers[k] = v
        response.write('POST,OPTIONS,HEAD')
        return response

    def __call__(self, request, remote_path, remote_method):

        ''' Handle a remote service call. '''

        global _middleware_cache

        self.request = request
        if request.method.lower() == 'options':
            return self.options()

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


## RemoteMethodDecorator
# This base class is for decorators that annotate remote service methods
class RemoteMethodDecorator(object):

    """ Indicates a class that can be used to decorate a remote method (a function on a class that responds to a remote API request). """

    args = None
    kwargs = None
    request = None
    service = None
    callback = None

    #lib = _libbridge
    #api = _apibridge
    #ext = _extbridge
    #util = _utilbridge

    def __init__(self, *args, **kwargs):

        """ Take in positional and keyword arguments when it is used as a decorator. """

        self.args = args
        self.kwargs = kwargs

    def __call__(self, fn):

        """ When the target remote method is called... """

        def wrapped(service_obj, request):

            """ Redirect the function call to our decorator's execute call (this enables us to do things like caching inside a decorator, by hijacking the remote method call and injecting a return value from the cache)... """

            self.callback = fn
            self.service = service_obj
            self.request = request

            for n in set(dir(fn)) - set(dir(self)):
                setattr(self, n, getattr(fn, n))

            return self.execute(*self.args, **self.kwargs)  # <-- redirect to our execute()

        return wrapped

    def execute(self, *args, **kwargs):

        """ Default decorator execution case: run the remote method (or, pass it down the chain to the next decorator) and return the result. """

        return self.execute_remote()

    def execute_remote(self):

        """ Shortcut to execute the remote method/next decorator and return the result. """

        return self.callback(self.service, self.request)

    def __repr__(self):

        """ Pleasant for debugging. """

        return self.callback


#### ==== Auditing Flags ==== ####

## Monitor
# Monitor individual and aggregate request data, and log to datastore or memcache
class Monitor(RemoteMethodDecorator):

    """ Log remote requests when they happen, and optionally store stats/usage per API consumer in the datastore and memcache. """

    def execute(self, *args, **kwargs):
        return self.execute_remote()


## Debug
# Set debug to true or false in the scope of a single remote method
class Debug(RemoteMethodDecorator):

    """ Set debug mode to true or false for a remote method. Adds extra debug flags to the response envelope and ups the logging level. """

    def execute(self):
        config.debug = True
        result = self.execute_remote()
        config.debug = False
        return result


## LogLevel
# Set the minimum log severity in the scope of a single remote method
class LogLevel(RemoteMethodDecorator):

    """ Manually set the logging level for a remote service method. """

    def execute(self):
        return self.execute_remote()


#### ==== Caching Flags ==== ####

## Cacheable
# Specify a method's caching policy for all caching layers.
class Cacheable(RemoteMethodDecorator):

    """ Indicate that the response from a remote method is cacheable locally on the browser side. """

    def execute(self, *args, **kwargs):
        return self.execute_remote()


## LocalCacheable
# Specify a method's caching policy for threadlocal/global layers.
class LocalCacheable(RemoteMethodDecorator):

    """ Indicate that the response from a remote method is cacheable in instance memory (fastcache). """

    def execute(self):
        return self.execute_remote()


## MemCacheable
# Specify a method's caching policy for memcaching.
class MemCacheable(RemoteMethodDecorator):

    """ Indicate that the response from a remote method is memcacheable. """

    def execute(self):
        return self.execute_remote()


#### ==== Security Flags ==== ####

## Blacklist
# Specify that a remote service client cannot be on a blacklist in order to execute successfully.
class Blacklist(RemoteMethodDecorator):

    """ Indicate that a remote method must be matched against a blacklist. """

    def execute(self, *args, **kwargs):
        return self.execute_remote()


## Whitelist
# Specify that a remote service client must be on a whitelist in order to execute successfully.
class Whitelist(RemoteMethodDecorator):

    """ Indicate that a remote method must be matched against a whitelist. """

    def execute(self, *args, **kwargs):
        return self.execute_remote()


## Authorize
# Specify that a remote service client must authorize via an ACL or other grouping of users.
class Authorize(RemoteMethodDecorator):

    """ Indicate that a remote method requires authorization. """

    def execute(self, *args, **kwargs):
        return self.execute_remote()


## Authenticate
# Specify that a remote service client must authenticate before executing remote methods.
class Authenticate(RemoteMethodDecorator):

    """ Indicate that a remote method requires authentication. """

    def execute(self):
        return self.execute_remote()


## AdminOnly
# Specify that a remote service method can be run by AppEngine-registered admins only.
class AdminOnly(RemoteMethodDecorator):

    """ Indicate that a remote method requires an admin to be logged in. """

    def execute(self):
        if self.api.users.is_current_user_admin():
            return self.execute_remote()
        else:
            raise Exception()


#### ==== Decorator Shortcuts ==== ####

# Audit decorators
audit = datastructures.DictProxy({

    'Monitor': Monitor,
    'Debug': Debug,
    'LogLevel': LogLevel,

})

# Caching decorators
caching = datastructures.DictProxy({

    'Cacheable': Cacheable,
    'LocalCacheable': LocalCacheable,
    'MemCacheable': MemCacheable,

})

# Security decorators
security = datastructures.DictProxy({

    'Authorize': Authorize,
    'Authenticate': Authenticate,
    'AdminOnly': AdminOnly

})


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


## rpcmethod - Wrap a classmethod for use with AppTools thimodels, optionally enforcing logon.
def rpcmethod(input, output=None, authenticated=False, audiences=_DEFAULT_OAUTH_AUDIENCES, scopes=_DEFAULT_OAUTH_SCOPES, **kwargs):

    ''' Wrap a service method with the appropriate decorators. '''

    from apptools import model

    # convert models to messages
    if issubclass(input, model.ThinModel):
        input = input.to_message_model()

    if output is None:
        output = input

    if not endpoints:
        def endpoint_wrap(fn):

            ''' Shim to wrap endpoint methods when the `endpoints` lib is unavailable. '''

            def wrap(*args, **kwargs):

                ''' Return the wrapped method directly, soaking up any endpoints arguments. '''

                return fn

            return wrap
    else:
        endpoint_wrap = endpoints.method

    def make_rpc_method(fn):

        ''' Closure that makes a closured RPC method. '''

        #@endpoint_wrap(input, output, audiences=audiences, scopes=scopes, **kwargs)
        #@remote.method(input, output)
        def wrapped(self, request):

            ''' Wrap remote method and throw an exception if no user is present. '''

            # pull user
            if authenticated:
                user = self.api.users.get_current_user()
                if not user:
                    raise self.LoginRequired("Woops! Only logged in users can do that!")
                result = fn(self, request, user)
            else:
                result = fn(self, request)
            if isinstance(result, model.ThinModel):
                return result.to_message()
            else:
                return result

        wrapped.__name__ = fn.__name__
        wrapped.__module__ = fn.__module__
        wrapped.__doc__ = fn.__doc__
        return endpoint_wrap(input, output, audiences=audiences, scopes=scopes, **kwargs)(remote.method(input, output)(wrapped))

    return make_rpc_method
