# -*- coding: utf-8 -*-

'''

AppTools Direct Service Dispatch

Use handlers/factories in this file for directly dispatching AppToolsPY service
classes.

-sam (<sam@momentum.io>)

'''

# Base Imports
import time
import config

# ProtoRPC Imports
from protorpc import remote
from protorpc import messages

# Service Imports
from apptools import services
from apptools.services import realtime
from apptools.services import _middleware_cache
from apptools.services import RemoteServiceHandler
from apptools.services import RemoteServiceHandlerFactory


## DirectServiceHandlerFactory - manufactures handlers with an injected request body
class DirectServiceHandlerFactory(RemoteServiceHandlerFactory):

	''' Modified ServiceHandlerFactory that injects an already-interpreted request body. '''

	def __call__(self, request, remote_path, remote_method):

		''' Handle a remote service call, via direct dispatch. '''

		global _middleware_cache

		if request.method.lower() == 'options':
			return self.options()

		# Extract response
		request.clock = {}
		request.clock['threadstart'] = time.time()
		request = request.response

		# Manufacture service + handler
		service = self.service_factory()
		service._initializeRemoteService()

		# Consider service middleware
		middleware = self._serviceConfig.get('middleware', False)
		if middleware is not False and len(middleware) > 0:

			for name, cfg in middleware:
				self.log('Considering %s middleware...' % name)
				if cfg.get('enabled', True):
					try:
						if name not in _middlware_cache or config.debug:
							middleware_class = webapp2.import_string(cfg['path'])
						else:
							middlware_class = _middleware_cache[name]

						middleware_object = middleware_class(debug=cfg['debug'], config=self._servicesConfig, opts=cfg.get('args', {}))
						service.middleware[name] = middleware_object

						if hasattr(middleware_object, 'before_request'):
							service, request, response = middleware_object.before_request(service, request, response)
							continue
						else:
							self.log('Middleware "%s" does not have pre_request method. Continuing.' % name)
							continue

					except Exception as e:
						self.error('Middleware "%s" raised an unhandled exception of type "%s".' % (name, e))
						if config.debug:
							raise
						else:
							continue
				else:
					self.log('Middleware "%s" is disabled.' % name)
					continue
		else:
			self.log('Middleware is disabled or there was none installed.')

		service_handler = DirectServiceFactory.new(DirectServiceHandler(self, service))
		service_handler.request = request
		service_handler.response = response

		self.log('Handler prepared... Dispatching.')
		service_handler.dispatch(self, service)


## DirectServiceHandler - allows preinjection of the interpreted request body
class DirectServiceHandler(RemoteServiceHandler):

	''' Service handler that allows direct dispatch of AppTools-based RPC services. '''

	def dispatch(self, factory, service):

		''' Dispatch remote request to handle(). '''

		import pdb; pdb.set_trace()

		# Map in factory / service
		self._ServiceHandler__factory = factory
		self._ServiceHandler__service = service

		# Attach handler / service
		service.handler = self
		self.service = service

		# Attach request / response
		request = self.request
		service.request = request

		service_path, remote_method = request.route_args
		self.handle(service_path, remote_method)
		self.run_post_action_middleware(service)
		return

	def handle(self, service_path, remote_method):

		''' Handle a remote service request via direct dispatch. '''

		# Map classes over
		self.service.handler = self

		state_initializer = self.service.initialize_request_state
		server_port = self.request.environ.get('SERVER_PORT', None)

		if server_port:
			server_port = int(server_port)
			request_state = realtime.RealtimeRequestState(**{
				'agent': None,
				'client': None,
				'remote_host': None,
				'remote_address': None,
				'server_host': None,
				'server_port': None,
				'service_path': '/_api/rpc/test',
				'protocol': 'realtime'
			})
			state_initializer(request_state)

		self.service.request = self.request
		self.service.response = self.response

		self.service.state['request'] = request_state

		if hasattr(self.service, 'initialize'):
			self.service.initialize()

		content_type = self._ServiceHandler__get_content_type()
		for mapper in self.installed_mappers:
			if content_type in mapper.content_types:
				break
		else:
			self.setstatus('failure')
			self._ServiceHandler__send_simple_error(415, 'Unsupported content-type: %s' % content_type)
			return
		try:
			try:
				try:
					method = getattr(self.service, remote_method)
					method_info = method.remote
				except AttributeError as e:
					self.setstatus('failure')
					self.__send_error(400, realtime.RealtimeRPCState.METHOD_NOT_FOUND_ERROR, 'Unrecognized RPC method: %s' % remote_method, mapper)
					return

				request = mapper.build_request(self, method_info.request_type)

			except (RequestError, messages.DecodeError) as e:
				self.setstatus('failure')
				self.__send_error(400, realtime.RealtimeRPCState.REQUEST_ERROR, 'Error parsing RPC request (%s).' % err, mapper)
				return

			try:
				response = method(request)
			except self.ApplicationError as e:
				self.setstatus('failure')
				self.__send_error(400, realtime.RealtimeRPCState.APPLICATION_ERROR, e.message, mapper, e.error_name)
				return

			mapper.build_response(self, response)

			if hasattr(self.service, 'after_request_hook'):
				self.service.after_request_hook()

		except Exception as e:
			self.setstatus('failure')
			self.logging.error('An unexpected error occurred when handling an RPC: %s' % err, exc_info=1)
			self.logging.exception('Unexpected service exception of type "%s": %s.' % (type(err), str(err)))
			self.__send_error(500, realtime.RealtimeRPCState.SERVER_ERROR, 'Internal Server Error', mapper)
			if config.debug:
				raise
			else:
				return

## DirectServiceFactory - manufactures service classes suitable for direct dispatch
class DirectServiceFactory(RemoteServiceFactory):

	''' Manufactures RemoteServices suitable for direct dispatch. '''

	@classmethod
	def new(cls, service):

		''' Prepares RemoteService classes. '''

		return service


def realtimeServiceMappings(svc_cfg, registry_path=None, handler=DirectServiceHandlerFactory):

	''' Generate a set of realtime service mappings, for use in URL routing. '''

	return services.generateServiceMappings(svc_cfg, registry_path, handler)
