# -*- coding: utf-8 -*-

'''

AppTools Direct Service Dispatch

Use handlers/factories in this file for directly dispatching AppToolsPY service
classes.

-sam (<sam@momentum.io>)

'''

# Base Imports
import time

# Service Imports
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


## DirectServiceHandler - allows preinjection of the interpreted request body
class DirectServiceHandler(RemoteServiceHandler):

	''' Service handler that allows direct dispatch of AppTools-based RPC services. '''

	def dispatch(self):
		pass

	def handle(self):
		pass


## DirectServiceFactory - manufactures service classes suitable for direct dispatch
class DirectServiceFactory(RemoteServiceFactory):
	pass
