# -*- coding: utf-8 -*-

"""
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
import logging
import webapp2

# apptools
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
    # remote / message packages
    from protorpc import remote
    from protorpc import registry
    from protorpc.remote import method as proto_method
    from protorpc.remote import Service as ProtoService

    # message packages
    from protorpc import messages as pmessages
    from protorpc.messages import Field as ProtoField
    from protorpc.messages import Message as ProtoMessage

    # message types
    from protorpc import message_types as pmessage_types
    from protorpc.message_types import VoidMessage as ProtoVoidMessage

    try:
        from protorpc.webapp import google_imports
    except:
        # must accept an already-monkeypatched lib
        pass
    else:
        # monkeypatch ``webapp`` for ``webapp2``
        google_imports.webapp = webapp2
        google_imports.template = object()
        google_imports.webapp_util = object()

    # grab service handlers
    from protorpc.webapp import forms
    from protorpc.webapp import service_handlers as handlers

    # webapp2 imports
    from webapp2_extras import protorpc as proto

except ImportError as e:

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
        _http_cfg = srvconfig.get('http', {})
        _oauth_cfg = srvconfig.get('oauth', {})
        _registry_cfg = srvconfig.get('registry', {})

        # copy in HTTP config, if any
        if len(_http_cfg):
            _DEFAULT_BASEPATH = _http_cfg.get('base', _DEFAULT_BASEPATH)
            _DEFAULT_GETPARAM = _http_cfg.get('request_param', _DEFAULT_GETPARAM)

        # copy in oauth config, if any
        if len(_oauth_cfg):
            _DEFAULT_OAUTH_SCOPES = _oauth_cfg.get('defaults', {}).get('scopes', _DEFAULT_OAUTH_SCOPES)
            _DEFAULT_OAUTH_AUDIENCES = _oauth_cfg.get('defaults', {}).get('audiences', _DEFAULT_OAUTH_AUDIENCES)

        # copy in registry config, if any
        if len(_registry_cfg):
            _DEFAULT_REGISTRY_PATH = _registry_cfg.get('path', _DEFAULT_REGISTRY_PATH)


    #### ==== Globals ==== ####
    _middleware_cache = {}
    _installed_mappers = []


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
        id = pmessages.StringField(3)  # integer or string ID for key
        namespace = pmessages.StringField(4)  # string namespace for key
        parent = pmessages.MessageField('Key', 5)  # recursive key message for parent


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

    ## ConfiguredClass - mixin class with config and logging tools.
    class ConfiguredClass(object):

        ''' Mixes-in config and logging tools. '''

        @decorators.memoize
        @decorators.classproperty
        def config(cls):

            ''' Resolve :py:class:`Service`-specific config.

                :returns: Configuration ``dict`` for the current
                          :py:class:`Service` class, if any. '''

            if config:
                config.config.get(cls._config_path)
            return {}

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


    ## RemoteServiceFactory - class for generating/preparing new RemoteService objects
    class RemoteServiceFactory(ConfiguredClass):

        ''' Responsible for manufacturing BaseService classes. '''

        _config_path = 'apptools.rpc.core.RemoteServiceFactory'

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
    class Service(ProtoService, ConfiguredClass):

        ''' Top-level parent class for ProtoRPC-based apptools services. '''

        # == Public Properties == #
        name = None
        version = None
        enabled = True

        # == Internal Properties == #
        _config_path = 'apptools.rpc.Service'

        # Mapped exceptions
        exceptions = datastructures.DictProxy({
            'ApplicationError': remote.ApplicationError
        })

        # Jinja2 integration
        context = {}
        context_injectors = []

        def initialize_request_state(self, state):

            ''' Request state hook from ``ProtoRPC``.

                :param state: State object handed in from ``ProtoRPC``,
                              which should be a descendent of the class
                              :py:class:`protorpc.remote.RequestState`. '''

            pass


    if appfactory and isinstance(appfactory, type(os)):

        from appfactory import integration

        ## AbstractPlatformServiceHandler - injects abstract root service handler mixins for AppFactory integration.
        class AbstractPlatformServiceHandler(core.BaseHandler, handlers.ServiceHandler, integration.AppFactoryMixin):

            ''' Injects AppFactory configuration, shortcut, and state properties. '''

            _appfactory_enabled = True

    else:

        ## AbstractPlatformServiceHandler - generic abstract root service handler.
        class AbstractPlatformServiceHandler(core.BaseHandler, handlers.ServiceHandler):

            ''' Used as a base platform service handler when no platform integration is enabled. '''

            _appfactory_enabled = False


    ## RemoteServiceHandler - this class is responsible for bridging a request to a remote service class, dispatching/executing to get the response, and returning it to the client.
    @platform.PlatformInjector
    class RemoteServiceHandler(AbstractPlatformServiceHandler, ConfiguredClass):

        ''' Handler for responding to remote API requests. '''

        _config_path = 'apptools.rpc.core.RemoteServiceHandler'

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

        # Middleware
        def run_post_action_middleware(self, service):

            ''' Run middleware that has a hook to run _after_ a request has been fulfilled by the RemoteService class. '''

            global global_debug
            global _middleware_cache

            middleware = self._servicesConfig.get('middleware', False)
            if middleware is not False and len(middleware) > 0:

                for name, middleware_object in service.middleware.items():
                    if _DEBUG:
                        self.logging.info('Considering ' + str(name) + ' middleware...')
                    try:

                        if hasattr(middleware_object, 'after_request'):
                            middleware_object.after_request(self.service, self.request, self.response)
                            continue
                        else:
                            if _DEBUG:
                                self.logging.info('Middleware ' + str(name) + ' does not have after_request method. Continuing.')
                            continue

                    except Exception, e:
                        if _DEBUG:
                            self.logging.error('Middleware "' + str(name) + '" raised an unhandled exception of type "' + str(e) + '".')
                        if (config and getattr(config, 'debug')) or (not config):
                            raise
                        continue

            else:
                if _DEBUG:
                    self.logging.info('Middleware is none or 0.')

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

        # Envelope Access
        def setstatus(self, status):

            ''' Set the status of a response. Good choices would be things like 'success' and 'error'. '''
            self._response_envelope['status'] = status
            return

        def __send_error(self, http_code, status_state, error_message, mapper, error_name=None):

            ''' Send an error RPC response. '''

            status = remote.RpcStatus(state=status_state, error_message=error_message, error_name=error_name)

            if isinstance(mapper, type(type)):
                mapper().build_response(self, status)
            else:
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

            if hasattr(self.service, 'state'):
                self.service.state['request'] = request_state

            # Check for initialize hook
            if hasattr(self.service, 'initialize'):
                self.service.initialize()

            if not content_type:
                self.setstatus('failure')
                self._ServiceHandler__send_simple_error(400, 'Invalid RPC request: missing content-type')
                return

            # Search for mapper to mediate request.
            for mapper in self._ServiceHandler__factory.installed_mappers:
                if content_type in mapper.content_types:
                    break
            else:
                self.setstatus('failure')
                self._ServiceHandler__send_simple_error(415, 'Unsupported content-type: %s' % content_type)
                return

            mapper = mapper()

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

                except (handlers.RequestError, pmessages.DecodeError), err:
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

                if not config:
                    baseHeaders = {}
                else:
                    baseHeaders = config.config.get('apptools.project.output', {}).get('headers', {})
                for k, v in baseHeaders.items():
                    if k.lower() == 'access-control-allow-origin':
                        if v is None:
                            if 'origin' in self.request.headers:
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
                if (not config) or config.debug:
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


    ## RemoteServiceFormsHandler - handle requests to the forms registry.
    class RemoteServiceFormsHandler(RemoteServiceHandler, ConfiguredClass):

        """ Handler for display HTML/javascript forms of ProtoRPC method calls.

            When accessed with no query parameters, will show a web page that displays
            all services and methods on the associated registry path.  Links on this
            page fill in the service_path and method_name query parameters back to this
            same handler.

            When provided with service_path and method_name parameters will display a
            dynamic form representing the request message for that method.  When sent,
            the form sends a JSON request to the ProtoRPC method and displays the
            response in the HTML page.

            Attribute:
                registry_path: Read-only registry path known by this handler. """

        _config_path = 'apptools.rpc.core.RemoteServiceFormsHandler'

        def __init__(self, request=None, response=None, registry_path=_DEFAULT_REGISTRY_PATH):

            """ Constructor - when configuring a FormsHandler to use with a webapp
                application do not pass the request handler class in directly.
                Instead use new_factory to ensure that the FormsHandler is
                created with the correct registry path for each request.

                :param request: :py:class:`webapp2.Response handed in by the framework. '''
                :param response: Empty :py:class:`webapp2.Response` to initialize.
                :keyword registry_path: Absolute path on server where the ProtoRPC RegsitryService is located. """

            assert registry_path
            self.registry_path = registry_path
            if request or response:
                self.request, self.response = request, response
                super(RemoteServiceHandler, self).__init__(request, response)

        def get(self):

            """ Send forms and method page to user. By default, displays a web page
                listing all services and methods registered on the server.
                Methods have links to display the actual method form.

                If both parameters are set, will display form for method.

                Query Parameters:
                  service_path: Path to service to display method of.  Optional.
                  method_name: Name of method to display form for.  Optional.

                :returns: Rendered template ``builtin/services/forms.html``. """

            params = {'forms_path': self.request.path.rstrip('/'),
                      'hostname': self.request.host,
                      'registry_path': self.registry_path,
                      }

            service_path = self.request.get('path', None)
            method_name = self.request.get('method', None)

            if service_path and method_name:
                form_template = 'builtin/services/methods.html'
                params['service_path'] = service_path
                params['method_name'] = method_name
            else:
                form_template = 'builtin/services/forms.html'

            return self.render(form_template, **params)

        @classmethod
        def new_factory(cls, registry_path=_DEFAULT_REGISTRY_PATH):

            """ Construct a factory for use with WSGIApplication. This method
                is called automatically with the correct registry path when
                services are configured via service_handlers.service_mapping.

                :param registry_path: Absolute path on server where the ProtoRPC
                                      RegsitryService is located.

                :returns: Factory function that creates a properly configured
                          FormsHandler instance. """

            def forms_factory():
                return cls(registry_path)
            return forms_factory

        def dispatch(self):

            ''' Dispatch a request through this handler. '''

            return self.get()


    ## RemoteServiceHandlerFactory - responsible for creating and preparing remote service handlers, which dispatch a request to a service class.
    @platform.PlatformInjector
    class RemoteServiceHandlerFactory(proto.ServiceHandlerFactory, ConfiguredClass):

        ''' Factory for preparing ServiceHandlers. '''

        _config_path = 'apptools.rpc.core.RemoteServiceHandlerFactory'

        @decorators.memoize
        @decorators.classproperty
        def outputConfig(cls):

            ''' Config channel for output config.
                :returns: Config ``dict`` for output
                          API subsystem, if any. '''

            if config:
                return config.config.get('apptools.project.output')
            return {'debug': True}

        @webapp2.cached_property
        def installed_mappers(self):

            ''' Return installed mappers, calculated from config. '''

            global _installed_mappers
            return _installed_mappers

        @classmethod
        def default(cls, service_factory, parameter_prefix=''):

            ''' Prepare the default setup for a service, including the appropriate RPC mappers. This is where we inject our custom JSONRPC mapper. '''

            ## Create Service
            factory = cls(service_factory)

            ## Add request mappers
            for mapper in factory.installed_mappers:
                factory.add_request_mapper(mapper())

            return factory

        def options(self):

            ''' Return a response to an HTTP OPTIONS request, enabling CORS and outputting supported methods. '''

            response = webapp2.Response()
            for k, v in self.outputConfig.get('headers').items():
                if k.lower() == 'access-control-allow-origin':
                    if v is None:
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

            # Consider service middleware
            middleware = self._servicesConfig.get('middleware', False)
            if middleware is not False and len(middleware) > 0:

                for name, cfg in middleware:
                    self.logging.debug('Considering ' + str(name) + ' middleware...')
                    if cfg['enabled'] is True:
                        try:
                            if name not in _middleware_cache or ((not config) or config.debug):
                                middleware_class = webapp2.import_string(cfg['path'])
                            else:
                                middleware_class = _middleware_cache[name]

                            middleware_object = middleware_class(debug=cfg['debug'], config=self._servicesConfig, opts=cfg.get('args', {}))
                            service.middleware[name] = middleware_object

                            if hasattr(middleware_object, 'before_request'):
                                service, request, response = middleware_object.before_request(service, request, response)
                                continue
                            else:
                                self.logging.debug('Middleware ' + str(name) + ' does not have pre_request method. Continuing.')
                                continue

                        except Exception, e:
                            self.logging.error('Middleware "' + str(name) + '" raise an unhandled exception of type "' + str(e) + '".')
                            if (not config) or config.debug:
                                raise
                            else:
                                continue

                    else:
                        self.logging.debug('Middleware ' + str(name) + ' is disabled.')
                        continue
            else:
                self.logging.debug('Middleware was none or 0.')

            service_handler = RemoteServiceFactory.new(RemoteServiceHandler(self, service))
            service_handler.request = request
            service_handler.response = response

            self.logging.info('Handler prepared. Dispatching...')

            service_handler.dispatch(self, service)


    ## ``_normalize_services`` - import services and generate paths.
    def _normalize_services(mixed_services):

        ''' _normalize_services - borrowed from webapp2. '''

        if isinstance(mixed_services, dict):
            mixed_services = mixed_services.iteritems()

        services = []
        for service_item in mixed_services:
            if isinstance(service_item, (list, tuple)):
                path, service = service_item
            else:
                path = None
                service = service_item

            if isinstance(service, basestring):
                # Lazily import the service class.
                service = webapp2.import_string(service)

            services.append((path, service))

        return services


    ## grab project-level service config, if any
    if srvconfig:
        _project_services = config.config.get('apptools.project.services')
    else:
        _project_services = {}


    ## ``_resolve_services`` - resolve installed service classes.
    def _resolve_services(svcs=_project_services, load=False):

        ''' Resolve installed service classes, optionally importing them as we go. '''

        services = []
        for service, cfg in svcs['services'].items():
            if cfg.get('enabled', True):
                urlpath = '/'.join(svcs.get('config', {}).get('url_prefix').split('/') + [service])
                servicepath = cfg['service']
                if load:
                    sp_split = servicepath.split('.')
                    servicepath = util._loadModule(('.'.join(sp_split[0:-1]), sp_split[-1]))
                services.append((urlpath, servicepath))
        return services


    ## ``_service_mappings`` - generate WSGI bindings for installed services.
    def _service_mappings(svc_cfg, registry_path=_DEFAULT_REGISTRY_PATH, handler=RemoteServiceHandlerFactory):

        ''' Utility function that reads the services config and generates URL mappings to service classes. '''

        ## Generate service mappings in tuple(<invocation_url>, <classpath>) format
        services = _normalize_services(_resolve_services(svc_cfg))
        mapping = []
        registry_map = {}

        if registry_path is not None:
            registry_service = registry.RegistryService.new_factory(registry_map)
            services = list(services) + [(registry_path, registry_service)]
            mapping.append((registry_path + r'/form(?:/)?', RemoteServiceFormsHandler))
            mapping.append((registry_path + r'/form/(.+)', forms.ResourceHandler))

        paths = set()
        for path, service in services:
            service_class = getattr(service, 'service_class', service)
            if not path:
                path = '/' + service_class.definition_name().replace('.', '/')

            if path in paths:
                raise handlers.ServiceConfigurationError(
                    'Path %r is already defined in service mapping'
                    % path.encode('utf-8'))
            else:
                paths.add(path)

            # Create service mapping for webapp2.
            new_mapping = handler.default(service).mapping(path)
            mapping.append(new_mapping)

            # Update registry with service class.
            registry_map[path] = service_class

        return mapping


    ## ``method`` - wrap a classmethod for use with AppTools thimodels, optionally enforcing logon.
    def method(input, output=None, audiences=_DEFAULT_OAUTH_AUDIENCES, scopes=_DEFAULT_OAUTH_SCOPES, **kwargs):

        ''' Wrap a service method with the appropriate decorators. '''

        # convert models to messages
        if issubclass(input, model.Model):
            input = input.to_message_model()

        if output is not None and issubclass(output, model.Model):
            output = output.to_message_model()

        if output is None:
            output = input

        def endpoint_wrap(fn, *args, **kwargs):

            ''' Shim to wrap endpoint methods when the `endpoints` lib is unavailable. '''

            def wrap(self, request):

                ''' Return the wrapped method directly, soaking up any endpoints arguments. '''

                result = fn(self, request)
                if isinstance(result, model.Model):
                    return result.to_message()
                return result

            # attach doc and fn name and return
            wrap.__name__ = fn.__name__
            wrap.__interface__ = tuple(args)
            wrap.__options__ = kwargs
            wrap.__doc__ = fn.__doc__
            wrap.__remote__ = True

            if fn.__doc__ is not None:
                wrap.__doc__ = fn.__doc__.strip()

            return proto_method(input, output)(wrap)

        return endpoint_wrap


    ## ``service`` - wrap a class and make it into a registered ``Service``.
    def service(*args, **kwargs):

        ''' Inject API service into config. '''

        global _project_services

        if len(args) == 1 and len(kwargs) == 0:
            klass = args[0]

            config_blob = {
                'enabled': True,
                'service': '.'.join(klass.__module__.split('.') + [klass.__name__]),
                'methods': klass._ServiceClass__remote_methods.keys(),
                'config': {
                    'caching': 'none',
                    'security': 'none',
                    'recording': 'none'
                }
            }

            # inject
            _project_services['services'][klass.name or klass.__name__] = config_blob
            return klass

    ## ``mapper`` - decorate a class as a service mapper.
    def mapper(klass):

        ''' Install the target ``klass`` as a ProtoRPC mapper. '''

        global _installed_mappers
        _installed_mappers.append(klass)
        return klass

Exceptions = datastructures.DictProxy
