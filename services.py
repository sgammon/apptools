# -*- coding: utf-8 -*-

# Basic imports
import base64
import config
import hashlib
import webapp2
import logging
import datetime

# Resolve JSON adapter
try:
	import json
except ImportError:
	try:
		from django.utils import json
	except ImportError:
		import simplejson as json

# ProtoRPC imports
import protorpc
from protorpc import remote
from protorpc import protojson
from protorpc import messages

# Message imports
from protorpc.messages import Field
from protorpc.messages import Variant

# Service handlers
from protorpc.webapp import service_handlers

# Lazy-loaded shortcut bridges
from apptools.core import _apibridge
from apptools.core import _extbridge

# Datastructures
from apptools.util import DictProxy

# Decorator imports
from apptools.decorators import audit
from apptools.decorators import caching
from apptools.decorators import security

# Extras import
from webapp2_extras import protorpc as proto

# New NDB import
from google.appengine.ext import ndb as nndb
from google.appengine.ext.ndb import key as nkey
from google.appengine.ext.ndb import model as nmodel


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
					if isinstance(item, list): # for repeated values...
						result[field.name] = [self.jsonForValue(x) for x in item]
					
			else:
				return super(_MessageJSONEncoder, self).default(value)
		else:
			return super(_MessageJSONEncoder, self).default(value)
			
		return result
		
	def jsonForValue(self, value):
		
		''' Return JSON for a given Python value. '''
		
		if isinstance(value, (basestring, int, float, bool)):
			return value
			
		elif isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
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

	_request = {

		'id': None,
		'opts': {},
		'agent': {}

	}

	def __init__(self):
		super(AppJSONRPCMapper, self).__init__()

	def encode_request(self, struct):
		
		''' Encode a request. '''
		
		encoded = _MessageJSONEncoder().encode(struct)
		return encoded

	def build_response(self, handler, response, response_envelope=None):

		''' Encode a response. '''

		try:
			response.check_initialized()
			if response_envelope is not None and handler is None:
				envelope = self.encode_request(self.envelope(response_envelope, response))
			else:
				envelope = self.encode_request(self.envelope(handler._response_envelope, response))

		except messages.ValidationError, err:
			raise ResponseError('Unable to encode message: %s' % err)
		else:
			if handler is not None: ## so we can inject responses...
				handler.response.headers['Content-Type'] = "application/json"
				handler.response.out.write(envelope)
			return envelope


	def envelope(self, wrap, response):
		
		''' Wrap the result of the request in a descriptive, helpful envelope. '''

		sysconfig = config.config.get('apptools.project')

		return {

			'id': wrap['id'],
			'status': wrap['status'],

			'response': {
				'content': response,
				'type': str(response.__class__.__name__)
			},

			'flags': wrap['flags'],
			'platform': {
				'debug': config.debug,
				'name': config.config.get('apptools.project').get('name', 'AppTools'),
				'version': '.'.join(map(lambda x: str(x), [sysconfig['version']['major'], sysconfig['version']['minor'], sysconfig['version']['micro']])),
				'build': sysconfig['version']['build'],
				'release': sysconfig['version']['release'],
				'engine': 'Providence/Clarity::v1.1 Embedded'
			}

		}


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
						existing_value = getattr(message, field.name)
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
					existing_value = getattr(message, field.name)
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
			except AttributeError, e:
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
class BaseService(remote.Service):
	
	''' Top-level parent class for ProtoRPC-based API services. '''
	
	# General stuff
	handler = None
	middleware = {}
	
	# State + config
	state = DictProxy({'request': DictProxy({'opts': {}, 'agent': {}, 'id': None}), 'opts': {}, 'service': {}})
	config = DictProxy({'global': {}, 'module': {}, 'service': {}})
	
	# Bridged shortcuts
	api = _apibridge
	_ext = _extbridge

	@webapp2.cached_property
	def globalConfig(self):
		
		''' Cached shortcut to services config. '''
		
		return config.config.get('apptools.services')
		
	def __init__(self, *args, **kwargs):
		super(BaseService, self).__init__(*args, **kwargs)
		
	def initiate_request_state(self, state):
		
		''' Copy over request state from ProtoRPC. '''
		
		super(RemoteService, self).initiate_request_state(state)

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
					for i in xrange(0, len(path)-1):
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
		self.state['service'][key] = value
		
	def _getstate(self, key, default=None):
		if key in self.state['service']:
			return self.state['service'][key]
		else: return default
		
	def _delstate(self, key):
		if key in self.state['service']:
			del self.state['service'][key]
		
	def __setitem__(self, key, value):
		self._setstate(key, value)
		
	def __getitem__(self, key):
		return self._getstate(key, None)
		
	def __delitem__(self, key):
		self._delstate(key)

	def __repr__(self):
		return '<RemoteService::'+'.'.join(self.__module__.split('.')+[self.__class__.__name__])+'>'
		
	def setflag(self, name, value):
		if self.handler is not None:
			return self.handler.setflag(name, value)
		
	def getflag(self, name):
		if self.handler is not None:
			return self.handler.getflag(name)

	## async response functionality
	def set_response(self, response):

		''' Add the response message model to the internal service state, so it can be passed to a followup task, so the followup task can fulfill & push it asynchronously. '''

		self._setstate('rmodel', response)
		return

	def prepare_followup(self, task=None, pipeline=None, start=False, *args, **kwargs):

		''' Prepare and set a followup task or pipeline, for async functionality. '''

		if task is not None:

			logging.info('Loading followup task.')
			logging.info('Task: '+str(task))
			logging.info('Args: '+str(args))
			logging.info('Kwargs: '+str(kwargs))

			if 'params' not in kwargs:
				kwargs['params'] = {}

			kwargs['params']['_token'] = self._getstate('token')
			kwargs['params']['_channel'] = self._getstate('channel')
			kwargs['params']['_rhash'] = self._getstate('rhash')
			kwargs['params']['_rid'] = self._getstate('rid')
			kwargs['params']['_rmodel'] = '.'.join(self._getstate('rmodel').__module__.split('.')+[self._getstate('rmodel').__class__.__name__])

			logging.info('Injected token, channel, rhash and rmodel path.')

			t = task(*args, **kwargs)

			logging.info('Instantiated task: ')
			logging.info('--args == '+str(args))
			logging.info('--kwargs == '+str(kwargs))

			if start:
				logging.info('Starting task.')
				self._setstate('followup', t.add())

				logging.info('Resulting task: "'+str(t)+'".')
				self.setflag('tid', str(t))

			return t

		elif pipeline is not None:

			logging.info('Loading followup pipeline.')
			logging.info('Pipeline: '+str(pipeline))
			logging.info('Args: '+str(args))
			logging.info('Kwargs: '+str(kwargs))

			kwargs['async_config'] = {
				'token': self._getstate('token'),
				'channel': self._getstate('channel'),
				'rid': self._getstate('rid'),
				'rhash': self._getstate('rhash'),
				'rmodel': '.'.join(self._getstate('rmodel').__module__.split('.')+[self._getstate('rmodel').__class__.__name__])
			}

			p = pipeline(*args, **kwargs)

			logging.info('Instantiated pipeline: "'+str(p)+'".')

			if start:
				logging.info('Starting pipeline.')

				self._setstate('followup', p.start())

				logging.info('Resulting pipeline: "'+str(p)+'".')
				self.setflag('pid', str(p.pipeline_id))

			return p

	def set_followup(self, tid=None, pid=None):

		''' Manually set the TID or PID response header. '''

		if tid is None:
			self.setflag('tid', str(tid))
		elif pid is None:
			self.setflag('pid', str(pid))
		return

	def go_async(self):

		''' Go into async mode. '''

		return self.handler.go_async()

	def can_async(self):

		''' Check if async mode is possible. '''

		return self.handler.can_async()

	## patched-through util methods
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

	_request_envelope = DictProxy({
		
		'id': None,
		'opts': {},
		'agent': {}

	})

	_response_envelope = DictProxy({

		'id': None,
		'flags': {},
		'status': 'ok'

	})
	interpreted_body = None	
	enable_async_mode = False


	# Config
	@webapp2.cached_property
	def servicesConfig(self):
		
		''' Cached shortcut to services config. '''
		
		return config.config.get('apptools.services')


	# Log Management
	def log(self, message):
		
		''' Logging shortcut. '''
		
		if self.servicesConfig['logging'] is True:
			if config.debug:
				handler = logging.info
			else:
				handler = logging.debug
			handler('ServiceHandler: '+str(message))

	def error(self, message):
		
		''' Error shortcut. '''
		
		logging.error('ServiceHandler ERROR: '+str(message))


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
			except Exception, e:
				self.interpreted_body = None
				return False
			else:
				return self.interpreted_body

	def can_async(self):

		''' Check and return whether an async response is possible. '''

		logging.info('CHECKING ASYNC CAPABILITY.')

		if 'alt' in self._request_envelope.opts:

			logging.info('1. `alt` flag found. value: "'+str(self._request_envelope.opts['alt'])+'".')

			if self._request_envelope.opts['alt'] == 'socket':

				if 'token' in self._request_envelope.opts:

					logging.info('2. `token` flag found. value: "'+str(self._request_envelope.opts['token'])+'".')

					if self._request_envelope.opts['token'] not in set(['', '_null_']):

						logging.info('3. `token` is not null or invalid. proceeding.')

						channel_token = self._get_channel_from_token(self._request_envelope.opts['token'])

						logging.info('4. pulled `channel_token`: "'+str(channel_token)+'".')

						if channel_token is not False:
							logging.info('5. ASYNC CAPABLE! :)')

							self.state['token'] = self._request_envelope.opts['token']
							self.state['channel'] = channel_token
							self.state['rhash'] = base64.b64encode(self.state['channel']+str(self._request_envelope['id']))
							return True
						else:
							logging.warning('Could not pull channel ID.')

							self.setflag('alt', 'denied')
							self.setflag('pushcmd', 'reconnect')
							return False
		return False

	def _get_channel_from_token(self, token):

		''' Resolve a channel ID/seed from the client's token. '''

		logging.info('Getting channel ID from token "'+str(token)+'".')

		## try memcache first
		token_key = self._get_token_key(token)

		logging.info('Token key calculated: "'+str(token_key)+'".')

		channel_id = _apibridge.memcache.get(token_key)
		if channel_id is None:

			logging.warning('Channel ID not found in memcache.')

			## try datastore if we can't find it in memcache
			from apptools.model import UserServicePushSession

			ups = nkey.Key(UserServicePushSession, token_key).get()
			if ups is not None:

				logging.info('PushSession found in megastore. Found seed "'+str(ups.seed)+'".')

				## if the model's found, set it in memecache
				_apibridge.memcache.set(token_key, {'seed': ups.seed, 'key': ups.key.urlsafe()})
				return ups.seed
			else:
				logging.error('PushSession not found in megastore. Invalid or discarded seed.')
				return False
		else:
			logging.info('Channel ID found in memcache. Returning!')
			return channel_id['seed']

	def _get_token_key(self, token):

		''' Encode and prefix a channel token, suitable for use as a key in memcache/megastore. '''

		return 'push_token::'+base64.b64encode(hashlib.sha256(token).hexdigest())


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
				self.log('Considering '+str(name)+' middleware...')
				try:

					if hasattr(middleware_object, 'after_request'):
						middleware_object.after_request(self.service, self.request, self.response)
						continue
					else:
						self.log('Middleware '+str(name)+' does not have after_request method. Continuing.')
						continue

				except Exception, e:
					self.error('Middleware "'+str(name)+'" raised an unhandled exception of type "'+str(e)+'".')
					if config.debug:
						raise
					continue

		else:
			self.log('Middleware is none or 0.')


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

	def log(self, message):
		
		''' Logging shortcut. '''
		
		if self.servicesConfig['logging'] is True:
			if config.debug:
				message_handler = logging.info
			else:
				message_handler = logging.debug
			message_handler('ServiceHandlerFactory: '+str(message))

	def error(self, message):
		
		''' Error shortcut. '''
		
		logging.error('ServiceHandlerFactory ERROR: '+str(message))

	@classmethod	
	def default(cls, service_factory, parameter_prefix=''):
		
		''' Prepare the default setup for a service, including the appropriate RPC mappers. This is where we inject our custom JSONRPC mapper. '''

		factory = cls(service_factory)

		# our nifty mapper, for correctly interpreting & providing our envelope schema
		jsonrpc = AppJSONRPCMapper()
		factory.add_request_mapper(jsonrpc)
		
		factory.add_request_mapper(service_handlers.ProtobufRPCMapper())
		factory.add_request_mapper(service_handlers.URLEncodedRPCMapper())

		return factory

	def __call__(self, request, remote_path, remote_method):
		
		''' Handle a remote service call. '''

		global _middleware_cache
		global_debug = config.debug

		# Extract response
		response = request.response

		# Manufacture service + handler
		service = self.service_factory()
		service._initializeRemoteService()

		# Consider service middleware
		middleware = self.servicesConfig.get('middleware', False)

		service_handler = RemoteServiceFactory.new(RemoteServiceHandler(self, service))
		service_handler.request = request
		service_handler.response = response

		if middleware is not False and len(middleware) > 0:

			for name, cfg in middleware:
				self.log('Considering '+str(name)+' middleware...')
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
							self.log('Middleware '+str(name)+' does not have pre_request method. Continuing.')
							continue

					except Exception, e:
						self.error('Middleware "'+str(name)+'" raise an unhandled exception of type "'+str(e)+'".')
						if config.debug:
							raise
						else:
							continue

				else:
					self.log('Middleware '+str(name)+' is disabled.')
					continue
		else:
			self.log('Middleware was none or 0.')

		self.log('Handler prepared. Dispatching...')

		service_handler.dispatch(self, service)