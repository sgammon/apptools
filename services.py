# -*- coding: utf-8 -*-

## Base imports
import base64
import config
import webapp2
import logging
import datetime

## Resolve a JSON import
try:
	import json
except ImportError:
	try:
		from django.utils import json
	except ImportError:
		import simplejson as json

## ProtoRPC imports
import protorpc

from protorpc import remote
from protorpc import protojson
from protorpc import messages

from protorpc.messages import Field
from protorpc.messages import Variant

from protorpc.webapp import service_handlers

## Datastructures
from apptools.util import DictProxy

## Decorator imports
from apptools.decorators import audit
from apptools.decorators import caching
from apptools.decorators import security

## Extras import
from webapp2_extras import protorpc as proto


## Service layer middleware cache
_middleware_cache = {}


## Expose service flags (middleware decorators)
flags = DictProxy({

	## Decorators related to logging/backend output
	'audit': DictProxy({
		'monitor': audit.Monitor,
		'debug': audit.Debug,
		'loglevel': audit.LogLevel,
	}),
	
	## Decorators related to caching, for performance
	'caching': DictProxy({
		'local': caching.LocalCacheable,
		'memcache': caching.MemCacheable,
		'cacheable': caching.Cacheable,
	}),
	
	## Decorators related to access & security
	'security': DictProxy({
		'authorize': security.Authorize,
		'authenticate': security.Authenticate,
		'admin': security.AdminOnly
	})

})

class VariantField(Field):

	''' Field definition for a completely variant field. '''

	VARIANTS = frozenset([Variant.DOUBLE, Variant.FLOAT, Variant.BOOL,
						  Variant.INT64, Variant.UINT64, Variant.SINT64,
						  Variant.INT32, Variant.UINT32, Variant.SINT32,
						  Variant.STRING, Variant.MESSAGE, Variant.BYTES, Variant.ENUM])

	DEFAULT_VARIANT = Variant.STRING

	type = (int, long, bool, basestring, dict, messages.Message)


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


# JSON encoder for messages
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
					if isinstance(item, list): ## for repeated values...
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

	def build_response(self, handler, response):

		''' Encode a response. '''

		try:
			response.check_initialized()
			envelope = self.encode_request(self.envelope(handler._response_envelope, response))

		except messages.ValidationError, err:
			raise ResponseError('Unable to encode message: %s' % err)
		else:
			handler.response.headers['Content-Type'] = "application/json"
			handler.response.out.write(envelope)
			return envelope


	def envelope(self, wrap, response):
		
		''' Wrap the result of the request in a descriptive, helpful envelope. '''

		sysconfig = config.config.get('apptools.project')
		if config.debug:
			debugflag = True

		return {

			'id': wrap['id'],
			'status': 'ok',

			'response': {
				'content': response,
				'type': str(response.__class__.__name__)
			},

			'flags': wrap['flags'],
			'platform': {
				'name': 'AppTools',
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

			handler._response_envelope['id'] = self._request['id']

			return self.decode_request(request_type, request_body['params'])

		except (messages.ValidationError, messages.DecodeError), err:
			raise service_handlers.RequestError('Unable to parse request content: %s' % err)


class RemoteServiceFactory(object):

	@classmethod
	def new(self, service):
		return service


## Top-Level Service Class
class RemoteService(remote.Service):
	
	''' Top-level parent class for ProtoRPC-based API services. '''
	
	handler = None
	middleware = {}
	state = {'request': {}, 'opts': {}, 'service': {}}
	config = {'global': {}, 'module': {}, 'service': {}}

	@webapp2.cached_property
	def globalConfig(self):
		
		''' Cached shortcut to services config. '''
		
		return config.config.get('apptools.services')
		
	def __init__(self, *args, **kwargs):
		super(RemoteService, self).__init__(*args, **kwargs)
		
	def initiate_request_state(self, state):
		
		''' Copy over request state from ProtoRPC. '''
		
		super(RemoteService, self).initiate_request_state(state)

	def _initializeRemoteService(self):
		
		''' Internal method for initializing a service and injecting it's config. '''

		##### ==== Step 1: Copy over global, module, and service configuration ==== ####
		
		## Copy global config
		self.config['global'] = self.globalConfig
		
		## Module configuration
		if hasattr(self, 'moduleConfigPath'):
			self.config['module'] = config.config.get(getattr(self, 'moduleConfigPath', '__null__'), {})

			## If we have a module + service config path, pull it from the module's branch
			if hasattr(self, 'configPath'):
				path = getattr(self, 'configPath').split('.')
				if len(path) > 0:
					fragment = self.config['module']
					for i in xrange(0, len(path)-1):
						if path[i] in fragment:
							fragment = fragment[path[i]]
					if isinstance(fragment, dict):
						self.config['service'] = fragment

		## No module configuration
		else:
			## Copy over default module config
			self.config['module'] = self.config['global']['defaults']['module']
			
			## If we have a service config path but no module config path...
			if hasattr(self, 'configPath'):
				## Try importing it as a top-level namespace
				toplevel = config.config.get(self.configPath, None)
				if toplevel is None:
					## If that doesn't work, copy it over from defaults...
					self.config['service'] = self.config['global']['defaults']['service']
				else:
					self.config['service'] = toplevel
					
			else:
				## If we have nothing, copy over defaults...
				self.config['service'] = self.config['global']['defaults']['service']
				

		##### ==== Step 2: Check for an initialize hook ==== ####
		if hasattr(self, 'initialize'):
			self.initialize()
		
	def _setstate(self, key, value):
		self.state['service'][key] = value
		
	def _getstate(self, key, default):
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
			

class RemoteServiceHandler(service_handlers.ServiceHandler):
	
	''' Handler for responding to remote API requests. '''

	## == Request/Response Containers == ##
	_response_envelope = {

		'id': None,
		'flags': {},
		'status': 'fail'

	}


	## == Config == ##
	@webapp2.cached_property
	def servicesConfig(self):
		
		''' Cached shortcut to services config. '''
		
		return config.config.get('apptools.services')


	## == Log Management == #
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


	## == Response Flags == ##
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


	## == Envelope Access == ##
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


	## == Middleware == ##
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


	## == Remote method execution == ##
	def dispatch(self, factory, service):
		
		''' Dispatch the remote request, and generate a response. '''
		
		# Unfortunately we need to access the protected attributes.
		self._ServiceHandler__factory = factory
		self._ServiceHandler__service = service

		## Link the service and handler both ways so we can pass stuff back and forth
		service.handler = self

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

		factory.add_request_mapper(service_handlers.ProtobufRPCMapper())
		factory.add_request_mapper(service_handlers.URLEncodedRPCMapper())
		factory.add_request_mapper(dialects.jsonrpc.AppJSONRPCMapper()) # <-- our nifty mapper, for correctly interpreting & providing our envelope schema

		return factory

	def __call__(self, request, remote_path, remote_method):
		
		''' Handle a remote service call. '''

		global _middleware_cache
		global_debug = config.debug

		## Extract response
		response = request.response

		## Manufacture service + handler
		service = self.service_factory()
		service._initializeRemoteService()

		## Consider service middleware
		middleware = self.servicesConfig.get('middleware', False)
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

		service_handler = RemoteServiceFactory.new(handler.RemoteServiceHandler(self, service))
		service_handler.request = request
		service_handler.response = response

		self.log('Handler prepared. Dispatching...')

		service_handler.dispatch(self, service)