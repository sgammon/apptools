# -*- coding: utf-8 -*-

# Base Imports
import os
import ndb
import config
import pprint
import random
import hashlib
import logging
import webapp2

# Useful Datastructures
from util import DictProxy
from util import ObjectProxy
from util import CallbackProxy
from util import _loadAPIModule

# Resolve a valid JSON adapter
try:
	import json
except ImportError:
	try:
		import simplejson as json
	except ImportError:
		try:
			from django.utils import simplejson as json
		except ImportError:
			logging.critical('No compatible JSON adapter found.')


## Webapp2
# AppTools uses [Webapp2](webapp-improved.appspot.com) for WSGI internals, session handling, request dispatching, and much more.
from webapp2 import Request
from webapp2 import Response
from webapp2 import RequestHandler
from webapp2_extras import jinja2
from webapp2_extras.appengine import sessions_ndb
from webapp2_extras.appengine import sessions_memcache

## Assets API
# AppTools includes an [asset management API](api/assets.html) for easily outputting links to static content.
from api import assets
from api.assets import AssetsMixin

## Output API
# AppTools includes an [integrated output API](api/output.html) for easily loading and executing Jinja2 templates.
# The output loader **automatically defaults to compiled templates** when running in production.
from api import output
from api.output import ModuleLoader
from api.output import CoreOutputLoader


## AppEngine API Bridge
# Lazy-loaded access to services, accessible from any apptools-based remote service, handler, model class or pipeline.
# Access this bridge from any class that extends BaseHandler, BaseService, BasePipeline or BaseModel via `self.api`.
"""
Example: `self.api.memcache.get(<samplekey>)`
"""
_apibridge = CallbackProxy(_loadAPIModule, {

	'db': ('google.appengine.ext', 'db'),
	'xmpp': ('google.appengine.api', 'xmpp'),
	'mail': ('google.appengine.api', 'mail'),
	'oauth': ('google.appengine.api', 'oauth'),
	'users': ('google.appengine.api', 'users'),
	'images': ('google.appengine.api', 'images'),
	'channel': ('google.appengine.api', 'channel'),
	'backends': ('google.appengine.api', 'backends'),
	'memcache': ('google.appengine.api', 'memcache'),
	'urlfetch': ('google.appengine.api', 'urlfetch'),
	'blobstore': ('google.appengine.ext', 'blobstore'),
	'taskqueue': ('google.appengine.api', 'taskqueue'),
	'capabilities': ('google.appengine.api', 'capabilities'),
	'identity': ('google.appengine.api', 'app_identity'),
	'multitenancy': ('google.appengine.api', 'namespace_manager'),
	'matcher': ('google.appengine.api', 'prospective_search')

})

## AppEngine Libraries Bridge
# Lazy-loaded bridge to common GAE libraries, with
# [NDB](http://code.google.com/p/appengine-ndb-experiment/),
# [Map/Reduce](http://code.google.com/p/appengine-mapreduce/), and
# [Pipelines](http://code.google.com/p/appengine-pipeline/) built in
_extbridge = CallbackProxy(_loadAPIModule, {

	'ndb': 'ndb',
	'pipelines': 'pipeline', 
	'mapreduce': 'mapreduce',

})

## Utility Library Bridge
# Lazy-loaded bridge to useful utility libraries, with
# [WTForms](http://wtforms.simplecodes.com/),
# [timesince](util/timesince.html),
# [byteconvert](util/byteconvert.html), and
# [httpagentparser](util/httpagentparser.html) built in
_utilbridge = CallbackProxy(_loadAPIModule, {
	
	'wtforms': 'wtforms',
	'timesince': ('apptools.util', 'timesince'),
	'byteconvert': ('apptools.util', 'byteconvert'),
	'httpagentparser': ('apptools.util', 'httpagentparser')

})

## BaseHandler
# Base request handler class, with shortcuts, utilities, and base template context
class BaseHandler(RequestHandler, AssetsMixin):

	''' Top-level parent class for request handlers in AppTools. '''
	
	# Class Properties
	configPath = 'apptools.project'
	minify = unicode
	response = Response
	context = {}
	uagent = {}
	
	# Bridge shortcuts
	api = _apibridge
	ext = _extbridge
	util = _utilbridge
		
	# Base HTTP Headers
	baseHeaders = {
		
		'Cache-Control': 'no-cache', # Stop caching of responses from Python, by default
		'X-Platform': 'AppTools/ProvidenceClarity-Embedded', # Indicate the platform that is serving this request
		'X-Powered-By': 'Google App Engine/1.5.5-prerelease', # Indicate the SDK version
		'X-UA-Compatible': 'IE=edge,chrome=1' # Enable compatibility with Chrome Frame, and force IE to render with the latest engine

	}
	
	# Base template context - available to every template except macros (for that, see template globals)
	@webapp2.cached_property
	def baseContext(self):
		
		''' Base template context - available to every template at runtime. '''

		return {
							
			'util': { # Utility stuff

				'request': { # Request Object
			
					'env': self.request.environ,
					'body': self.request.body,
					'headers': self.request.headers,
					'method': self.request.method,
					'scheme': self.request.scheme,
					'remote_user': self.request.remote_user,
					'remote_addr': self.request.remote_addr,
					'host': self.request.host,
					'host_url': self.request.host_url,
					'path': self.request.path,
					'query_string': self.request.query_string,
					'hash': os.environ.get('REQUEST_ID_HASH'),
					'namespace': _apibridge.multitenancy.get_namespace()
					
				},
				
				'appengine': { # App Information
				
					'instance': os.environ.get('INSTANCE_ID'),
					'current_version': os.environ.get('CURRENT_VERSION_ID'),
					'datacenter': os.environ.get('DATACENTER'),
					'software': os.environ.get('SERVER_SOFTWARE'),
					'backend': _apibridge.backends.get_backend()
				
				},

				'env': os.environ, # Main Environ
				'config': { # Main Config
					'get': config.config.get,
					'debug': config.debug,
					'project': self._projectConfig
				},
				
				'converters': {	# Converters
					'json': json, # SimpleJSON or Py2.7 JSON
					'timesince': self.util.timesince, # Util library for "15 minutes ago"-type text from datetimes
					'byteconvert': self.util.byteconvert # Util library for formatting data storage amounts
				},
				
				'random': { # Random
					'random': random.random,
					'randint': random.randint,
					'randrange': random.randrange
				},
				
				'pprint': pprint.pprint,
			},
		
			'api': { # API Shortcuts
		
				'users': {
					'is_current_user_admin': _apibridge.users.is_current_user_admin,
					'current_user': _apibridge.users.get_current_user,
					'create_login_url': _apibridge.users.create_login_url,
					'create_logout_url': _apibridge.users.create_logout_url
				},
				'backends': _apibridge.backends,
				'multitenancy': _apibridge.multitenancy
		
			},

			'page': { # Page flags
				'ie': False, # when set to True, will serve an (ie.css)[assets/style/source/ie.html] stylesheet
				'mobile': False, # when set to True, will serve a (mobile.css)[assets/style/source/mobile.html] stylesheet
				'appcache': { # enable/disable HTML5 appcaching
					'enabled': False,
					'location': None,
				}
			},			
			
		}
	

	def dispatch(self):
		
		''' Sniff the Uagent header, then pass off to Webapp2. '''
		
		# Sniff Uagent
		if self.request.headers.get('User-Agent', None) is not None:
			try:
				# Pass through httpagentparser
				self.uagent = self.util.httpagentparser.detect(self.request.headers.get('User-Agent'))
			except Exception, e:
				logging.warning('Exception encountered parsing uagent: '+str(e))
				pass
		
		# Dispatch method (GET/POST/etc.)
		return super(BaseHandler, self).dispatch()


	# Cached access to Jinja2
	@webapp2.cached_property
	def jinja2(self):
		
		''' Cached access to Jinja2. '''
		
		return jinja2.get_jinja2(app=self.app, factory=self.jinja2EnvironmentFactory)
		
	
	# Returns a prepared Jinja2 environment.
	def jinja2EnvironmentFactory(self, app):

		''' Returns a prepared Jinja2 environment. '''

		templates_compiled_target = self._jinjaConfig.get('compiled_path')
		use_compiled = not config.debug or self._jinjaConfig.get( 'force_compiled')

		if templates_compiled_target is not None and use_compiled:
			# Use precompiled templates loaded from a module or zip.
			loader = ModuleLoader(templates_compiled_target)
		else:
			loader = CoreOutputLoader(self._jinjaConfig.get('template_path'))

		j2cfg = self._jinjaConfig
		j2cfg['environment_args']['loader'] = loader
		
		# Inject python builtins as globals, so they are available to macros
		
		# **Ever wanted your favorite Python builtins available in your template?** Look ma!
		j2cfg['globals'] = {
		
			'all': all, 'any': any,
			'int': int, 'str': str,
			'len': len, 'map': map,
			'max': max, 'min': min,
			'zip': zip, 'bool': bool,
			'list': list, 'dict': dict,
			'tuple': tuple, 'range': range,
			'round': round, 'slice': slice,
			'xrange': xrange, 'filter': filter,
			'reduce': reduce, 'sorted': sorted,
			'unicode': unicode,	'reversed': reversed,
			'isinstance': isinstance, 'issubclass': issubclass,

			'link': webapp2.uri_for, # Standalone uri_for shortcut

			'asset': { # Bridge to the Assets API
			
				'url': self.get_asset,		
				'image': self.get_img_asset,
				'style': self.get_style_asset,
				'script': self.get_script_asset
			
			},

			'util': {
				'converters': {
					'json': json
				},
				'api': _apibridge,
				'ext': _extbridge
			},
			
			'sys': {
				'debug': config.debug,
				'version':	str(self._sysConfig['version']['major'])+'.'+str(self._sysConfig['version']['minor'])+' '+str(self._sysConfig['version']['release'])
			}
	
		}
		
		environment = jinja2.Jinja2(app, config=j2cfg) # Make & return template environment
		return environment

	# Bind runtime template context variables (overridden in sub handlers to allow injection into the template context)
	def _bindRuntimeTemplateContext(self, basecontext):

		''' Bind variables to the template context related to the current request context. '''

		# Detect if we're handling a request from IE, and if we are, tell the template context
		context['page'] = {
		
			'ie': False, ## are we serving to IE?
			'mobile': False, ## are we serving to mobile?
			'appcache': {
				'enabled': False, ## enable/disable appcaching
				'location': None, ## location for appcache manifest
			},
			'services': {
				'services_manifest': self.make_services_manifest(),
				'global_config': self._globalServicesConfig
			}, ## enable API services
		
		}
		
		if self.uagent is not None and len(self.uagent) > 0:
			## Detect if we're handling a request from IE, and if we are, tell the template context
			if self.uagent['browser']['name'] == 'MSIE':
				context['page']['ie'] = True
		
		return context

	
	def make_services_manifest(self):

		''' Generate a struct we can pass to the page in JSON that describes API services. ''' 

		## Generate list of services to expose to user
		svcs = []
		opts = {}

		jsapi_cache = self.api.memcache.get('apptools//services_manifest')
		if jsapi_cache is not None:
			return jsapi_cache
		else:
			for name, config in self._servicesConfig['services'].items():
				if config['enabled'] is True:

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
						svcs.append((name, service_action_url, config, opts))

					elif security_profile['expose'] == 'admin':
						if users.is_current_user_admin():
							svcs.append((name, service_action_url, config, opts))

					elif security_profile['expose'] == 'none':
						continue

			self.api.memcache.set('apptools//services_manifest', svcs)
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
	def minify(self, rendered_template):
		
		''' Minify rendered template output. Override for custom minification function or monkeypatch to 'unicode' to disable completely. '''
		
		import slimmer
	
		minify = unicode ## default to unicode
		
		# Read minification config + setup minification handler
		if self._outputConfig.get('minify', False) is True:
			if content_type == 'text/html':
				minify = slimmer.html_slimmer
			elif content_type == 'text/javascript':
				from slimmer.js_function_slimmer import slim as slimjs
				minify = slimjs
			elif content_type == 'text/css':
				minify = slimmer.css_slimmer
				
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
				raise ## in production, the show must go on...
			else:
				pass
							
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

		return config.config.get('apptools.project.services')

	@webapp2.cached_property
	def _sysConfig(self):

		''' Cached shortcut to handler config. '''

		return self.config.get(self.configPath)

	@webapp2.cached_property
	def _outputConfig(self):

		''' Cached shortcut to output config. '''

		return self.config.get(self.configPath+'.output')

	@webapp2.cached_property
	def _projectConfig(self):

		''' Cached shortcut to project config. '''

		return self.config.get('apptools.project')

	@webapp2.cached_property
	def _jinjaConfig(self):

		''' Cached shortcut to Jinja2 config. '''

		return self.config.get('webapp2_extras.jinja2')