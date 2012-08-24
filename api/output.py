# -*- coding: utf-8 -*-

'''

API: Output

Responsible for the task of finding and compiling templates to be sent to the browser.
Two levels of caching are implemented here - in-memory handler caching and memcache.

According to settings in the config.py, this module will attempt to load compiled
template code from the handler first, memcache second, and at last resort will compile
the template and store it in the cache.

-sam (<sam@momentum.io>)

'''

## Base Imports
import os
import base64
import config
import pprint
import random
import hashlib
import webapp2

## API Mixins
from apptools.api import CoreAPI
from apptools.api import HandlerMixin

## Utils
from apptools.util import json

## Log + Exceptions
from apptools.exceptions import AppException
from apptools.util.debug import AppToolsLogger

## Webapp2 Imports
from webapp2 import cached_property
from webapp2_extras import jinja2

## Jinja2 Imports
from jinja2 import FileSystemLoader as JFileSystemLoader
from jinja2.exceptions import TemplateNotFound

## Globals
t_data = {}
logging = AppToolsLogger('apptools.core', 'OutputAPI')


## CoreOutputAPIException
# Root exception class for all Output API-related exceptions.
class CoreOutputAPIException(AppException):

    ''' Root exception class for all Output API-related exceptions. '''

    pass


## ModuleLoader
# Loader that resolves templates compiled into Python modules.
class ModuleLoader(object):

    ''' Loads templates that have been compiled into Python modules. '''

    has_source_access = False

    @cached_property
    def loaderConfig(self):

        ''' Cached template loader configuration. '''

        return config.config.get('apptools.project.output.template_loader')

    @cached_property
    def logging(self):

        ''' Log pipe. '''

        global logging
        return logging.extend(name='ModuleLoader')._setcondition(self.loaderConfig.get('loaders', {}).get('logging', False))

    def __init__(self, templatemodule):

        ''' Loads a template from a module. '''

        self.modules = {}
        self.logging.info('Loading templatemodule: "%s".' % templatemodule)
        self.templatemodule = templatemodule

    def prepare_template(self, environment, filename, tpl_vars, globals):

        ''' Prepare a template to be returned after it has been loaded. '''

        t = object.__new__(environment.template_class)
        t.environment = environment
        t.globals = globals
        t.name = tpl_vars['name']
        t.filename = filename
        t.blocks = tpl_vars['blocks']

        # render function and module
        t.root_render_func = tpl_vars['root']
        t._module = None

        # debug and loader helpers
        t._debug_info = tpl_vars['debug_info']
        t._uptodate = lambda: True

        return t

    def load(self, environment, filename, globals=None, prepare=True):

        ''' Loads a pre-compiled template, stored as Python code in a template module. '''

        if globals is None:
            globals = {}

        # Strip '/' and remove extension.
        filename, ext = os.path.splitext(filename.strip('/'))
        self.logging.debug('Loading template at path "%s" with extension "%s".' % (filename, ext))

        try:
            if filename not in self.modules:
                # Store module to avoid unnecessary repeated imports.
                self.modules[filename] = self.get_module(environment, filename)

            if prepare:
                tpl_vars = self.modules[filename].run(environment)

        except Exception, e:
            self.logging.exception('Encountered exception during template module import: "%s".' % e)
            raise e

        else:
            if prepare:
                return self.prepare_template(environment, filename, tpl_vars, globals)
            else:
                return self.modules[filename]

    def get_module(self, environment, template):

        ''' Converts a template path to a package path and attempts import, or else raises Jinja2's TemplateNotFound. '''

        # Convert the path to a module name.
        module_name = self.templatemodule + '.' + template.replace('/', '.')
        prefix, obj = module_name.rsplit('.', 1)

        try:
            self.logging.info('Template module at path "%s" for template path "%s" was found and is valid.' % (module_name, template))
            return getattr(__import__(prefix, None, {'environment': environment}, [obj]), obj)
        except (ImportError, AttributeError):
            t = TemplateNotFound(template)
            self.logging.error('Template module at path "%s" for template path "%s" could not be found or is not valid.' % (module_name, template))
            self.logging.exception('TemplateNotFound exception was thrown: "%s".' % t)
            raise t


# Source caching
def get_tdata_from_fastcache(name, do_log):

    ''' Get template data from fastcache (instance memory). '''

    global t_data
    if name in t_data:
        if do_log:
            logging.info('OUTPUT_LOADER: Found bytecode in fastcache memory under key \'' + str(base64.b64encode(name)) + '\'.')
        return t_data[name]
    else:
        return None


def set_tdata_to_fastcache(name, data, do_log):

    ''' Save template data to fastcache (instance memory). '''

    global t_data
    t_data[name] = data
    if do_log:
        logging.info('OUTPUT_LOADER: Set template \'' + str(name) + '\' to fastcache memory.')


# Memcache API loader
def get_tdata_from_memcache(name, do_log):

    ''' Get template data from memcache. '''

    from apptools.core import _apibridge
    data = _apibridge.memcache.get('Core//Output//Template-' + name)
    if data is not None:
        if do_log:
            logging.info('OUTPUT_LOADER: Found bytecode in memcache under key \'tdata-' + str(name) + '\'.')
        return data
    else:
        return None


def set_tdata_to_memcache(name, data, do_log):

    ''' Set template data to memcache. '''

    from apptools.core import _apibridge
    _apibridge.memcache.set('Core//Output//Template-' + name, data)
    if do_log:
        logging.info('OUTPUT_LOADER: Set template \'' + str(name) + '\' to memcache under key \'Core//Output//Template-' + str(name) + '\'.')


## CoreOutputLoader
# Main, filesystem-based template loader, backed by instance/thread memory and memcache.
class CoreOutputLoader(JFileSystemLoader):

    ''' Loads templates and automatically inserts bytecode caching logic for both fastcache (instance memory) and memcache. '''

    has_source_access = True

    @cached_property
    def logging(self):

        ''' Log pipe. '''

        global logging
        return logging.extend(name='FileSystemLoader')._setcondition(self.loaderConfig.get('loaders', {}).get('logging', False))

    @cached_property
    def devConfig(self):

        ''' Cached dev configuration. '''

        return config.config.get('apptools.system.dev')

    @cached_property
    def loaderConfig(self):

        ''' Cached template loader configuration. '''

        return config.config.get('apptools.project.output.template_loader')

    def get_source(self, environment, name):

        ''' Overrides Jinja's default FileSystemLoader get_source to provide it via memcache or instance memory, if available. '''

        # Load config
        y_cfg = self.loaderConfig

        # Encode in Base64
        b64_name = base64.b64encode(name)

        # Debug logging
        if y_cfg.get('debug') == True:
            do_log = True
        else:
            do_log = False
        if do_log:
            self.logging.debug('Template requested for name \'' + str(name) + '\'.')

        # Don't do caching if we're in dev mode
        if not config.debug or self.loaderConfig['force'] is True:

            # Try the in-memory supercache
            if y_cfg.get('use_memory_cache') == True:
                source = get_tdata_from_fastcache(b64_name, do_log)
            else:
                source = None

            if source is None:  # Not found in fastcache

                if do_log:
                    self.logging.debug('Template not found in fastcache.')

                # Fallback to memcache
                if y_cfg.get('use_memcache') == True:
                    source = get_tdata_from_memcache(b64_name, do_log)

                # Fallback to regular loader, then cache
                if source is None:  # Not found in memcache

                    if do_log:
                        self.logging.debug('Template not found in memcache.')
                    source, name, uptodate = super(CoreOutputLoader, self).get_source(environment, name)

                    if y_cfg.get('use_memcache') != False:
                        set_tdata_to_memcache(b64_name, source, do_log)

                    if y_cfg.get('use_memory_cache') != False:
                        set_tdata_to_fastcache(b64_name, source, do_log)

        else:  # In dev mode, compile everything every time

            source, name, uptodate = super(CoreOutputLoader, self).get_source(environment, name)
            return source, name, uptodate

        # Return compiled template code
        return source, name, lambda: True


## CoreOutputAPI
# Used to tie together everything needed for proper output abstraction.
class CoreOutputAPI(CoreAPI):

    ''' Contains utils, methods and properties related to outputting data with AppTools. '''

    # Cached access to Jinja2
    def get_jinja(self, app, factory):

        ''' Cached access to Jinja2. '''

        return jinja2.get_jinja2(app=app, factory=factory)

_api = CoreOutputAPI()


## OutputMixin
# Used as an addon class for base classes like BaseHandler to bridge in access to the Core Output API.
class OutputMixin(HandlerMixin):

    ''' Bridge the Core Output API to methods on a handler. '''

    minify = unicode
    _output_api = _api
    _response_headers = {}

    # Cached access to Jinja2
    @cached_property
    def jinja2(self):

        ''' Cached access to Jinja2. '''

        return self._output_api.get_jinja(self.app, self.jinja2EnvironmentFactory)

    @cached_property
    def _outputConfig(self):

        ''' Cached shortcut to output config. '''

        return self.config.get('.'.join(self.configPath.split('.') + ['output']))

    @cached_property
    def _jinjaConfig(self):

        ''' Cached shortcut to Jinja2 config. '''

        return self.config.get('webapp2_extras.jinja2')

    # Base HTTP response headers
    @webapp2.cached_property
    def baseHeaders(self):

        ''' Base HTTP response headers - returned with every request. '''

        if 'X-AppFactory-Frontline' in self.request.headers:
            self._response_headers['X-Platform'] = self.request.headers.get('X-AppFactory-Frontline')

        if config.debug:
            self._response_headers.update({
                'X-Debug': 'True',
                'Cache-Control': self._outputConfig.get('headers', {}).get('Cache-Control', 'no-cache'),  # Stop caching of responses from Python, by default
                'X-Powered-By': self._outputConfig.get('headers', {}).get('X-Powered-By', 'Google AppEngine/1.6.5 %s/%s' % (self._projectConfig['name'], '.'.join(map(str, [self._projectConfig['version']['major'], self._projectConfig['version']['minor'], self._projectConfig['version']['micro']])))),  # Indicate the SDK version
                'X-UA-Compatible': self._outputConfig.get('headers', {}).get('X-UA-Compatible', 'IE=edge,chrome=1'),  # Enable compatibility with Chrome Frame, and force IE to render with the latest engine
                'Access-Control-Allow-Origin': self._outputConfig.get('headers', {}).get('Access-Control-Allow-Origin', '*')  # Enable Cross Origin Resource Sharing (CORS)
            })
        else:
            self._response_headers.update({
                'Cache-Control': self._outputConfig.get('headers', {}).get('Cache-Control', 'private; max-age=600'),  # Stop caching of responses from Python, by default
                'X-UA-Compatible': self._outputConfig.get('headers', {}).get('X-UA-Compatible', 'IE=edge,chrome=1'),  # Enable compatibility with Chrome Frame, and force IE to render with the latest engine
                'Access-Control-Allow-Origin': self._outputConfig.get('headers', {}).get('Access-Control-Allow-Origin', '*')  # Enable Cross Origin Resource Sharing (CORS)
            })
        return self._response_headers

    # Base template context - available to every template, including macros (injected into Jinja2 globals)
    @webapp2.cached_property
    def baseContext(self):

        ''' Base template context - available to every template at runtime. '''

        return self.injectContext({

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

                'handler': self,
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

                },

                'env': os.environ,  # Main Environ
                'config': {  # Main Config

                    'get': config.config.get,
                    'debug': config.debug,
                    'strict': config.strict,
                    'system': self._sysConfig,
                    'project': self._projectConfig,

                    'services': {
                        'global': self._globalServicesConfig,
                        'project': self._servicesConfig
                    }

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
                    'randrange': random.randrange,
                    'choice': random.choice

                },

                'pprint': pprint.pprint,
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
                'version':  ''.join(map(lambda x: str(x), [self._projectConfig['version']['major'], '.', self._projectConfig['version']['minor'], ' ', self._projectConfig['version']['release']]))

            }
        })

    # Cached access to the current template environment
    @cached_property
    def template_environment(self):

        ''' Return a new environment, because if we're already here it's not cached. '''

        return self.jinja2EnvironmentFactory(self.request.app)

    def injectContext(self, context):

        ''' Run attached context injectors. '''

        if hasattr(self, 'context_injectors'):
            ## Consider context injectors
            for injector in self.context_injectors:
                try:
                    newcontext = injector(self, context)
                except Exception, e:
                    self.logging.warning('Context injector "' + str(injector) + '" encountered an unhandled exception. ' + str(e))
                    if config.debug:
                        raise
                    else:
                        continue
                else:
                    context = newcontext

        return context

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
        j2cfg['filters'] = {'json': json.dumps}

        environment = jinja2.Jinja2(app, config=j2cfg)  # Make & return template environment
        return environment

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

        ''' Return a response containing a rendered Jinja2 template. '''

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
        return self.response
