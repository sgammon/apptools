# -*- coding: utf-8 -*-

## Base Imports
import logging

## Util Imports
from apptools.util import DictProxy

class RemoteMethodDecorator(object):
	
	''' Indicates a class that can be used to decorate a remote method (a function on a class that responds to a remote API request). '''
	
	args = None
	kwargs = None
	request = None
	service = None	
	callback = None
	
	def __init__(self, *args, **kwargs):
		
		''' Take in positional and keyword arguments when it is used as a decorator. '''
		
		self.args = args
		self.kwargs = kwargs

	def __call__(self, fn):

		''' When the target remote method is called... '''

		def wrapped(service_obj, request):

			''' Redirect the function call to our decorator's execute call (this enables us to do things like caching inside a decorator, by hijacking the remote method call and injecting a return value from the cache)... '''

			self.callback = fn
			self.service = service_obj
			self.request = request

			for n in set(dir(fn)) - set(dir(self)):
				setattr(self, n, getattr(fn, n))
		
			return self.execute(*self.args, **self.kwargs) # <-- redirect to our execute()
		
		return wrapped
		
	def execute(self, *args, **kwargs):
		
		''' Default decorator execution case: run the remote method (or, pass it down the chain to the next decorator) and return the result. '''
		
		return self.execute_remote()
		
	def execute_remote(self):
		
		''' Shortcut to execute the remote method/next decorator and return the result. '''
		
		return self.callback(self.service, self.request)
		
	def __repr__(self):
		
		''' Pleasant for debugging. '''
		
		return self.callback
		

## Auditing Flags
class Monitor(RemoteMethodDecorator):

	''' Log remote requests when they happen, and optionally store stats/usage per API consumer in the datastore and memcache. '''

	def execute(self, *args, **kwargs):
		return self.execute_remote()


class Debug(RemoteMethodDecorator):

	''' Set debug mode to true or false for a remote method. Adds extra debug flags to the response envelope and ups the logging level. '''

	def execute(self):
		return self.execute_remote()


class LogLevel(RemoteMethodDecorator):

	''' Manually set the logging level for a remote service method. '''

	def execute(self):
		return self.execute_remote()
		

## Caching Flags
class Cacheable(RemoteMethodDecorator):
	
	''' Indicate that the response from a remote method is cacheable locally on the browser side. '''

	def execute(self, *args, **kwargs):
		return self.execute_remote()


class LocalCacheable(RemoteMethodDecorator):

	''' Indicate that the response from a remote method is cacheable in instance memory (fastcache). '''

	def execute(self):
		return self.execute_remote()

	
class MemCacheable(RemoteMethodDecorator):

	''' Indicate that the response from a remote method is memcacheable. '''

	def execute(self):
		return self.execute_remote()

		
## Security Flags
class Authorize(ServiceFlag):
	
	''' Indicate that a remote method requires authorization. '''

	def execute(self, *args, **kwargs):
		return self.execute_remote()


class Authenticate(ServiceFlag):

	''' Indicate that a remote method requires authentication. '''

	def execute(self):
		return self.execute_remote()

	
class AdminOnly(ServiceFlag):

	''' Indicate that a remote method requires an admin to be logged in. '''

	def execute(self):
		return self.execute_remote()
		

## Shortcuts to decorators
audit = DictProxy({

	## Decorators for monitoring/auditing/backend storage of remote service calls

	'Monitor': Monitor,
	'Debug': Debug,
	'LogLevel': LogLevel,

})

caching = DictProxy({

	## Decorators for caching at various levels

	'Cacheable': Cacheable,
	'LocalCacheable': LocalCacheable,
	'MemCacheable': MemCacheable,

})

security = DictProxy({

	## Decorators for enforcing authentication or authorization policy on a remote method

	'Authorize': Authorize,
	'Authenticate': Authenticate,
	'AdminOnly': AdminOnly

})