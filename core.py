# -*- coding: utf-8 -*-

# Base Imports
import os
import config
import pprint
import random
import hashlib
import webapp2

# Datastructures
from apptools.util import json
from apptools.util import _loadModule
from apptools.util import CallbackProxy
from apptools.util import AppToolsLogger

## Webapp2
# AppTools uses [Webapp2](webapp-improved.appspot.com) for WSGI internals, session handling, request dispatching, etc.
from webapp2 import Response
from webapp2 import RequestHandler
from webapp2_extras import jinja2

## Assets API
# AppTools includes an [asset management API](api/assets.html) for easily outputting links to static or dynamic images, js, stylesheets, or other site assets.
from api.assets import AssetsMixin

## Output API
# AppTools includes an [integrated output API](api/output.html) for easily loading and executing Jinja2 templates.
# The output loader **automatically defaults to compiled templates** when running in production.
from api.output import ModuleLoader
from api.output import CoreOutputLoader


## AppEngine API Bridge
# Lazy-loaded access to services, accessible from any apptools-based remote service, handler, model class or pipeline.
# Access this bridge from any class that extends BaseHandler, BaseService, BasePipeline or BaseModel via `self.api`.
'''
Example: `self.api.memcache.get(<samplekey>)`
'''
_apibridge = CallbackProxy(_loadModule, {

    'db': ('google.appengine.ext', 'db'),
    'xmpp': ('google.appengine.api', 'xmpp'),
    'mail': ('google.appengine.api', 'mail'),
    'quota': ('google.appengine.api', 'quota'),
    'oauth': ('google.appengine.api', 'oauth'),
    'users': ('google.appengine.api', 'users'),
    'files': ('google.appengine.api', 'files'),
    'search': ('google.appengine.api', 'search'),
    'images': ('google.appengine.api', 'images'),
    'channel': ('google.appengine.api', 'channel'),
    'matcher': ('google.appengine.api', 'prospective_search'),
    'backends': ('google.appengine.api', 'backends'),
    'memcache': ('google.appengine.api', 'memcache'),
    'urlfetch': ('google.appengine.api', 'urlfetch'),
    'identity': ('google.appengine.api', 'app_identity'),
    'blobstore': ('google.appengine.ext', 'blobstore'),
    'taskqueue': ('google.appengine.api', 'taskqueue'),
    'logservice': ('google.appengine.api', 'logservice'),
    'conversion': ('google.appengine.api', 'conversion'),
    'capabilities': ('google.appengine.api', 'capabilities'),
    'multitenancy': ('google.appengine.api', 'namespace_manager'),
    'app_identity': ('google.appengine.api', 'app_identity'),
    'prospective_search': ('google.appengine.api', 'prospective_search')

})

## AppEngine Libraries Bridge
# Lazy-loaded bridge to common GAE libraries, with
# [NDB](http://code.google.com/p/appengine-ndb-experiment/),
# [Map/Reduce](http://code.google.com/p/appengine-mapreduce/), and
# [Pipelines](http://code.google.com/p/appengine-pipeline/) built in
'''
Example: `self.ext.mapreduce.control.start_map(<name>, <reader>, <map_params>)`
'''
_extbridge = CallbackProxy(_loadModule, {

    'ndb': ('google.appengine.ext', 'ndb'),
    'pipelines': 'pipeline',
    'mapreduce': 'mapreduce'

})

## Utility Library Bridge
# Lazy-loaded bridge to useful utility libraries, with
# [timesince](util/timesince.html),
# [byteconvert](util/byteconvert.html), and
# [httpagentparser](util/httpagentparser.html) built in
'''
Example: `self.util.timesince(<from_datetime>, <now>)`
'''
_utilbridge = CallbackProxy(_loadModule, {

    'timesince': ('apptools.util.timesince', 'timesince'),
    'byteconvert': ('apptools.util.byteconvert', 'humanize_bytes'),
    'httpagentparser': ('apptools.util.httpagentparser', 'detect')

})

## Lib Utility Bridge
# Lazy-loaded bridge to libraries installed in lib/dist & managed by buildout. By default, this includes:
# [Jinja2], (http://jinja.pocoo.org/docs/),
# [WTForms](http://wtforms.simplecodes.com/),
# [Logbook](http://packages.python.org/Logbook/), and
# [slimmer](http://pypi.python.org/pypi/slimmer)
'''
Example: `self.lib.slimmer(<code>, <syntax>, <hardcore>)`
'''
_libbridge = CallbackProxy(_loadModule, {

    'jinja2': 'jinja2',
    'wtforms': 'wtforms',
    'logbook': 'logbook',
    'slimmer': ('slimmer', 'slimmer'),

})

## Logging Controller
# This will soon replace PY's builtin logging system.
logging = AppToolsLogger('apptools.core')


## BaseHandler
# Base request handler class, with shortcuts, utilities, and base template context.
class BaseHandler(RequestHandler, AssetsMixin):

    ''' Top-level parent class for request handlers in AppTools. '''

    # Class Properties
    configPath = 'apptools.project'
    minify = unicode
    response = Response
    context = {}
    uagent = {}

    # Bridge shortcuts
    api = _apibridge  # Shortcuts to AppEngine APIs
    ext = _extbridge  # Shortcuts to AppTools plugins
    lib = _libbridge  # Shortcuts to lib/ and lib/dist libraries
    util = _utilbridge  # Shortcuts to utilities

    # Base HTTP Headers
    @webapp2.cached_property
    def logging(self):
        global logging
        return logging.extend('RequestHandler', self.__class__.__name__)

    @webapp2.cached_property
    def baseHeaders(self):

        ''' Base HTTP response headers - returned with every request. '''

        return {

            'Cache-Control': self._outputConfig.get('headers', {}).get('Cache-Control', 'no-cache'),  # Stop caching of responses from Python, by default
            'X-Powered-By': self._outputConfig.get('headers', {}).get('X-Powered-By', 'Google AppEngine/1.6.4-prerelease %s/%s' % (self._sysConfig['name'], '.'.join(map(str, [self._sysConfig['version']['major'], self._sysConfig['version']['minor'], self._sysConfig['version']['micro']])))),  # Indicate the SDK version
            'X-UA-Compatible': self._outputConfig.get('headers', {}).get('X-UA-Compatible', 'IE=edge,chrome=1'),  # Enable compatibility with Chrome Frame, and force IE to render with the latest engine
            'Access-Control-Allow-Origin': self._outputConfig.get('headers', {}).get('Access-Control-Allow-Origin', '*')  # Enable Cross Origin Resource Sharing (CORS)
        }

    # Base template context - available to every template, including macros (injected into Jinja2 globals)
    @webapp2.cached_property
    def baseContext(self):

        ''' Base template context - available to every template at runtime. '''

        return {

            # Python Builtins
            'all': all, 'any': any,
            'int': int, 'str': str,
            'len': len, 'map': map,
            'max': max, 'min': min,
            'enumerate': enumerate,
            'zip': zip, 'bool': bool,
            'list': list, 'dict': dict,
            'tuple': tuple, 'range': range,
            'round': round, 'slice': slice,
            'xrange': xrange, 'filter': filter,
            'reduce': reduce, 'sorted': sorted,
            'unicode': unicode, 'reversed': reversed,
            'isinstance': isinstance, 'issubclass': issubclass,

            'link': webapp2.uri_for,  # Standalone uri_for shortcut

            'util': {  # Utility stuff

                'logging': self.logging.extend('apptools.templates', 'Context'),  # Handy logging bridge

                'request': {  # Request Object

                    'env': self.request.environ,  # request environment variables
                    'body': self.request.body,  # request body
                    'headers': self.request.headers,  # request HTTP headers
                    'method': self.request.method,  # request HTTP method
                    'scheme': self.request.scheme,  # request scheme (HTTP/HTTPS)
                    'remote_user': self.request.remote_user,  # request remote user
                    'remote_addr': self.request.remote_addr,  # request remote IP
                    'host': self.request.host,  # request hostname
                    'host_url': self.request.host_url,  # request host URL
                    'path': self.request.path,  # request HTTP path
                    'query_string': self.request.query_string,  # request query string
                    'hash': os.environ.get('REQUEST_ID_HASH'),  # request hash (from Google)
                    'namespace': _apibridge.multitenancy.get_namespace()  # current namespace

                },

                'appengine': {  # App Information

                    'instance': os.environ.get('INSTANCE_ID'),
                    'current_version': os.environ.get('CURRENT_VERSION_ID'),
                    'datacenter': os.environ.get('DATACENTER'),
                    'software': os.environ.get('SERVER_SOFTWARE'),
                    'backend': _apibridge.backends.get_backend()

                },

                'env': os.environ,  # Main Environ
                'config': {  # Main Config

                    'get': config.config.get,
                    'debug': config.debug,
                    'project': self._projectConfig

                },

                'converters': {  # Converters

                    'json': json,  # SimpleJSON or Py2.7 JSON
                    'hashlib': hashlib,
                    'timesince': self.util.timesince,  # Util library for "15 minutes ago"-type text from datetimes
                    'byteconvert': self.util.byteconvert  # Util library for formatting data storage amounts

                },

                'random': {  # Random

                    'random': random.random,
                    'randint': random.randint,
                    'randrange': random.randrange

                },

                'pprint': pprint.pprint,
            },

            'api': {  # API Shortcuts

                'users': _apibridge.users,
                'backends': _apibridge.backends,
                'multitenancy': _apibridge.multitenancy

            },

            'page': {  # Page flags
                'ie': False,  # when set to True, will serve an (ie.css)[assets/style/source/ie.html] stylesheet
                'mobile': False,  # when set to True, will serve a (mobile.css)[assets/style/source/mobile.html] stylesheet
                'appcache': {  # enable/disable HTML5 appcaching

                    'enabled': False,
                    'location': None,

                }
            },

            'asset': {  # Bridge to the Assets API

                'url': self.get_asset,  # generate a URL for an asset (low level method)
                'image': self.get_img_asset,  # generate a URL for an image asset
                'style': self.get_style_asset,  # generate a URL for a stylesheet asset
                'script': self.get_script_asset  # generate a URL for a javascript asset

            },

            'sys': {

                'debug': config.debug,  # dev_appserver/production flag (if true, you're running on localhost)
                'version':  ''.join(map(lambda x: str(x), [self._sysConfig['version']['major'], '.', self._sysConfig['version']['minor'], ' ', self._sysConfig['version']['release']]))

            }
        }

    def dispatch(self):

        ''' Sniff the Uagent header, then pass off to Webapp2. '''

        # Sniff Uagent
        if self.request.headers.get('User-Agent', None) is not None:
            try:
                # Pass through httpagentparser
                self.uagent = self.util.httpagentparser(self.request.headers.get('User-Agent'))
            except Exception, e:
                self.logging.warning('Exception encountered parsing uagent: ' + str(e))
                pass

        # Dispatch method (GET/POST/etc.)
        return super(BaseHandler, self).dispatch()

    def handle_exception(self, exception, debug):

        ''' Handle an unhandled exception during method dispatch. '''

        self.logging.exception('Unhandled exception encountered in RequestHandler code: "%s".' % exception)
        if debug:
            raise
        else:
            self.error(500)

    # Cached access to Jinja2
    @webapp2.cached_property
    def jinja2(self):

        ''' Cached access to Jinja2. '''

        return jinja2.get_jinja2(app=self.app, factory=self.jinja2EnvironmentFactory)

    # Returns a prepared Jinja2 environment.
    def jinja2EnvironmentFactory(self, app):

        ''' Returns a prepared Jinja2 environment. '''

        templates_compiled_target = self._jinjaConfig.get('compiled_path')
        use_compiled = not config.debug or self._jinjaConfig.get('force_compiled')

        if templates_compiled_target is not None and use_compiled:
            # Use precompiled templates loaded from a module or zip.
            loader = ModuleLoader(templates_compiled_target)
        else:
            loader = CoreOutputLoader(self._jinjaConfig.get('template_path'))

        j2cfg = self._jinjaConfig
        j2cfg['environment_args']['loader'] = loader

        # Inject python builtins as globals, so they are available to macros

        # **Ever wanted your favorite Python builtins available in your template?** Look ma!
        j2cfg['globals'] = self.baseContext

        environment = jinja2.Jinja2(app, config=j2cfg)  # Make & return template environment
        return environment

    # Bind runtime template context variables (overridden in sub handlers to allow injection into the template context)
    def _bindRuntimeTemplateContext(self, context):

        ''' Bind variables to the template context related to the current request context. '''

        # Detect if we're handling a request from IE, and if we are, tell the template context
        context['page'] = {

            'ie': False,  # are we serving to IE?
            'mobile': False,  # are we serving to mobile?
            'tablet': False,
            'appcache': {
                'enabled': False,  # enable/disable appcaching
                'location': None,  # location for appcache manifest
            },
            'services': {
                'services_manifest': self.make_services_manifest(),
                'global_config': self._globalServicesConfig
            },  # enable API services

        }

        if self.uagent is not None and len(self.uagent) > 0:

            ## Detect if we're handling a request from IE, and if we are, tell the template context
            if 'MSIE' in self.uagent.get('browser', {}).get('name', ''):
                self.logging.debug('Uagent detected as Microsoft Internet Explorer.')
                context['page']['ie'] = True

            ## Detect Android clients
            elif 'Android' in self.uagent.get('browser', {}).get('name', ''):
                self.logging.debug('Uagent detected as Android.')
                context['page']['mobile'] = True

            ## Detect iPhone clients
            elif 'iPhone' in self.uagent.get('browser', {}).get('name', ''):
                self.logging.debug('Uagent detected as iPhone.')
                context['page']['mobile'] = True

            ## Detect iPad clients
            elif 'iPad' in self.uagent.get('browser', {}).get('name', ''):
                self.logging.debug('Uagent detected as iPad.')
                context['page']['mobile'] = True
                context['page']['tablet'] = True

        return context

    def make_services_manifest(self):

        ''' Generate a struct we can pass to the page in JSON that describes API services. '''

        ## Generate list of services to expose to user
        svcs = []
        opts = {}

        self.logging.dev('Generating services manifest...')
        for name, config in self._servicesConfig['services'].items():

            self.logging.dev('Considering API "%s"...' % name)
            if config['enabled'] is True:

                self.logging.dev('API is enabled.')
                security_profile = self._globalServicesConfig['middleware_config']['security']['profiles'].get(config['config']['security'], None)

                caching_profile = self._globalServicesConfig['middleware_config']['caching']['profiles'].get(config['config']['caching'], None)

                if security_profile is None:

                    ## Pull default profile if none is specified
                    security_profile = self._globalServicesConfig['middleware_config']['security']['profiles'][self._globalServicesConfig['defaults']['service']['config']['security']]

                if caching_profile is None:
                    caching_profile = self._globalServicesConfig['middleware_config']['caching']['profiles'][self._globalServicesConfig['defaults']['service']['config']['caching']]

                ## Add caching to local opts
                opts['caching'] = caching_profile['activate'].get('local', False)

                ## Grab prefix
                service_action = self._servicesConfig['config']['url_prefix'].split('/')

                ## Add service name
                service_action.append(name)

                ## Join into endpoint URL
                service_action_url = '/'.join(service_action)

                ## Expose depending on security profile
                if security_profile['expose'] == 'all':
                    self.logging.dev('API is exposed publicly.')
                    svcs.append((name, service_action_url, config, opts))

                elif security_profile['expose'] == 'admin':
                    self.logging.dev('API is exposed to admins only.')
                    if _apibridge.users.is_current_user_admin():
                        self.logging.dev('User valid for API access.')
                        svcs.append((name, service_action_url, config, opts))

                elif security_profile['expose'] == 'none':
                    self.logging.dev('API is set to expose to `none`.')
                    continue
            else:
                self.logging.dev('API is disabled.')

        return svcs

    def _setcontext(self, *args, **kwargs):

        ''' Take a data structure (list of tuples, dict, or kwargs) and assign the appropriate k, v to the template context. '''

        if len(kwargs) > 0:
            for k, v in kwargs.items():
                self.context[k] = v

        if len(args) > 0:
            for arg in args:
                if isinstance(arg, list):
                    if isinstance(arg[0], tuple):
                        for k, v in arg:
                            self.context[k] = v
                elif isinstance(arg, dict):
                    for k, v in arg.items():
                        self.context[k] = v
        return

    # Minify
    def minify(self, rendered_template, content_type='text/html'):

        ''' Minify rendered template output. Override for custom minification function or monkeypatch to 'unicode' to disable completely. '''

        import slimmer

        minify = unicode  # default to unicode

        # Read minification config + setup minification handler
        if self._outputConfig.get('minify', False) is True:
            if content_type == 'text/html':
                minify = slimmer.html_slimmer
                self.logging.debug('Minifying with HTMLSlimmer...')
            elif content_type == 'text/javascript':
                from slimmer.js_function_slimmer import slim as slimjs
                minify = slimjs
                self.logging.debug('Minifying with SlimJS...')
            elif content_type == 'text/css':
                minify = slimmer.css_slimmer
                self.logging.debug('Minifying with SlimCSS...')
            else:
                self.logging.debug('No minification enabled.')

        return minify(rendered_template)

    # Render a template, given a context, with Jinja2
    def render(self, path, context={}, elements={}, content_type='text/html', headers={}, **kwargs):

        ''' Return a response containing a rendered Jinja template. Creates a session if one doesn't exist. '''

        if isinstance(self.context, dict) and len(self.context) > 0:
            tmp_context = self.context
            self.context = self.baseContext
            map(self._setcontext, tmp_context)
        else:
            self.context = self.baseContext

        # Build response HTTP headers
        response_headers = {}
        for key, value in self.baseHeaders.items():
            response_headers[key] = value
        if len(headers) > 0:
            for key, value in headers.items():
                response_headers[key] = value

        # Consider kwargs
        if len(kwargs) > 0:
            for k, v in kwargs.items():
                self.context[k] = v

        # Bind runtime-level template context
        try:
            self.context = self._bindRuntimeTemplateContext(self.context)
        except NotImplementedError, e:
            if config.debug:
                raise e
            else:
                pass  # in production, the show must go on...

        # Bind elements
        map(self._setcontext, elements)

        # Render template and write
        self.response.write(self.minify(self.jinja2.render_template(path, **self.context)))

        # Set response headers & content type
        self.response.headers = [(key, value) for key, value in response_headers.items()]
        self.response.content_type = content_type

        # Finished!
        return

    ## Config Shortcuts
    @webapp2.cached_property
    def config(self):

        ''' Cached shortcut to global config '''

        return config.config

    @webapp2.cached_property
    def _globalServicesConfig(self):

        ''' Cached shortcut to the global services config. '''

        return config.config.get('apptools.services')

    @webapp2.cached_property
    def _servicesConfig(self):

        ''' Cached shortcut to the project services config. '''

        return self.config.get('.'.join(self.configPath.split('.') + ['services']))

    @webapp2.cached_property
    def _sysConfig(self):

        ''' Cached shortcut to handler config. '''

        return self.config.get(self.configPath)

    @webapp2.cached_property
    def _outputConfig(self):

        ''' Cached shortcut to output config. '''

        return self.config.get('.'.join(self.configPath.split('.') + ['output']))

    @webapp2.cached_property
    def _projectConfig(self):

        ''' Cached shortcut to project config. '''

        return self.config.get(self.configPath)

    @webapp2.cached_property
    def _jinjaConfig(self):

        ''' Cached shortcut to Jinja2 config. '''

        return self.config.get('webapp2_extras.jinja2')
