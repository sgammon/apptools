# -*- coding: utf-8 -*-

## Base Imports
import os
import ndb
import config
import pprint
import random
import hashlib
import logging
import slimmer
import webapp2

## Utilities
from util import timesince
from util import byteconvert
from util import httpagentparser

## Assets API Bridge
from api.assets import AssetsMixin

## Output Components
from api.output import ModuleLoader
from api.output import CoreOutputLoader

## Resolve JSON Adapter
try:
	import json
except ImportError:
	try:
		import simplejson as json
	except ImportError:
		logging.critical('No compatible JSON adapter found.')

# Webapp2 Imports
from webapp2 import Request
from webapp2 import Response
from webapp2 import RequestHandler
from webapp2_extras import jinja2
from webapp2_extras.appengine import sessions_ndb
from webapp2_extras.appengine import sessions_memcache

# Datastructure Imports (shamelessly borrowed from Providence/Clarity)
from util import DictProxy
from util import ObjectProxy
from util import CallbackProxy

_api_cache = {}


def _loadAPIModule(entry):
	
	''' Callback to lazy-load an API module in tuple(path, item) format. '''
	
	global _api_cache

	if entry not in _api_cache:
		if isinstance(entry, tuple):
			path, name = entry
			mod = __import__(path, globals(), locals(), [name])
			_api_cache[entry] = getattr(mod, name)
		elif isinstance(entry, basestring):
			mod = __import__(entry, globals(), locals(), ['*'])
			_api_cache[entry] = mod
		else:
			logging.error('Lazyloader failed to resolve module for shortcut: "'+str(entry)+'".')
			raise ImportError, "Could not resolve module for entry '"+str(entry)+"'."
		
	return _api_cache[entry]
	
_apibridge = CallbackProxy(_loadAPIModule, {

	''' Lazy-loaded bridge to AppEngine API services. '''

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

_extbridge = CallbackProxy(_loadAPIModule, {

	''' Lazy-loaded bridge to useful AppEngine libs. '''

	'ndb': 'ndb',
	'pipelines': 'pipeline',
	'mapreduce': 'mapreduce',

})


class BaseHandler(RequestHandler, AssetsMixin):

	''' Top-level parent class for request handlers in AppTools. '''
	
	## 1: Class variables
	configPath = 'apptools.project'
	minify = unicode
	response = Response
	context = {}
	uagent = {}
	
	## 2: Shortcuts
	api = _apibridge
	ext = _extbridge
		
	## 3: HTTP Headers included in every response
	baseHeaders = {
	
		''' HTTP headers added to every response (override via headers kwarg on `render`). '''
		
		'Cache-Control': 'no-cache', # Stop caching of responses from Python, by default
		'X-Platform': 'AppTools/ProvidenceClarity-Embedded', # Indicate the platform that is serving this request
		'X-Powered-By': 'Google App Engine/1.5.5-prerelease', # Indicate the SDK version
		'X-UA-Compatible': 'IE=edge,chrome=1' # Enable compatibility with Chrome Frame, and force IE to render with the latest engine

	}
	
	## 4: Base template context
	@webapp2.cached_property
	def baseContext(self):
		
		''' Base template context - available to every template at runtime. '''	
	
		logging.info('REQUEST ENVIRON: '+str(self.request.environ))
	
		return {
			
			## Python builtins
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
			
			## Anchors and assets
			'link': self.url_for,
			'asset': {
			
				## Link to the Assets API
			
				'url': self.get_asset,			
				'image': self.get_img_asset,
				'style': self.get_style_asset,
				'script': self.get_script_asset
			
			},
			
			## System stuff
			'version': str(self._sysConfig['version']['major'])+'.'+str(self._sysConfig['version']['minor'])+' '+str(self._sysConfig['version']['release']),			
	
			## Utility stuff
			'util': {

				## Request Information
				'request': {
			
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
				
				## App Information
				'appengine': {
				
					'instance': os.environ.get('INSTANCE_ID'),
					'current_version': os.environ.get('CURRENT_VERSION_ID'),
					'datacenter': os.environ.get('DATACENTER'),
					'software': os.environ.get('SERVER_SOFTWARE'),
					'backend': _apibridge.backends.get_backend()
				
				},

				'env': os.environ,
				'config': {
					'get': config.config.get,
					'debug': config.debug,
					'project': self._projectConfig
				},
				'converters': {
					'json': json, ## SimpleJSON or Py2.7 JSON
					'timesince': timesince.timesince, ## Util library for "15 minutes ago"-type text from datetimes
					'byteconvert': byteconvert.humanize_bytes ## Util library for formatting data storage amounts
				},
				'random': {
					'random': random.random,
					'randint': random.randint,
					'randrange': random.randrange
				},
				'pprint': pprint.pprint,
			},
		
			## API Shortcuts
			'api': {
		
				'users': {
					'is_current_user_admin': _apibridge.users.is_current_user_admin,
					'current_user': _apibridge.users.get_current_user,
					'create_login_url': _apibridge.users.create_login_url,
					'create_logout_url': _apibridge.users.create_logout_url
				},
				'backends': _apibridge.backends,
				'multitenancy': _apibridge.multitenancy
		
			}
			
		}
	

	## 5: Internal methods
	def dispatch(self):
		
		''' Sniff the Uagent header, then pass off to Webapp2. '''
		
		# Parse useragent
		if self.request.headers.get('User-Agent', None) is not None:
			try:
				self.uagent = httpagentparser.detect(self.request.headers.get('User-Agent'))
			except Exception, e:
				logging.warning('Exception encountered parsing uagent: '+str(e))
				pass
		return super(BaseHandler, self).dispatch()
	
	@webapp2.cached_property
	def config(self):
		
		''' Cached shortcut to global config. '''
		
		return config.config

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

	@webapp2.cached_property
	def jinja2(self):
		
		''' Cached access to Jinja2. '''
		
		return jinja2.get_jinja2(app=self.app, factory=self.jinja2EnvironmentFactory)
		
	def jinja2EnvironmentFactory(self, app):

		''' Returns a prepared Jinja2 environment. '''

		templates_compiled_target = self._jinjaConfig.get('compiled_path')
		use_compiled = not config.debug or self._jinjaConfig.get( 'force_compiled')

		if templates_compiled_target is not None and use_compiled:
			# Use precompiled templates loaded from a module or zip.
			loader = ModuleLoader(templates_compiled_target)
		else:
			# Parse templates for every new environment instances.
			loader = CoreOutputLoader(self._jinjaConfig.get('template_path'))

		self._jinjaConfig['environment_args']['loader'] = loader
		environment = jinja2.Jinja2(app, config=self._jinjaConfig)

		return environment

	def _bindRuntimeTemplateContext(self):

		''' Bind variables to the template context related to the current request context. '''

		raise NotImplementedError("_bindRuntimeTemplateContext is not implemented in %s." % str(self.__class__))

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
		
	## 5: Public methods		
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
			
		# Read minification config + setup minification handler
		if self._outputConfig.get('minify', False) is True:
			if content_type == 'text/html':
				self.minify = slimmer.html_slimmer
			elif content_type == 'text/javascript':
				from slimmer.js_function_slimmer import slim as slimjs
				self.minify = slimjs
			elif content_type == 'text/css':
				self.minify = slimmer.css_slimmer
			else:
				self.minify = unicode ## be careful about minifying things we don't know about...
				
		## Bind elements
		map(self._setcontext, elements)
		
		## Render template and write
		self.response.write(self.minify(self.jinja2.render_template(path, **self.context)))
		
		## Set response headers & content type
		self.response.headers = [(key, value) for key, value in response_headers.items()]
		self.response.content_type = content_type
		
		## Finished!
		return