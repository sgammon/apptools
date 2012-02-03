# -*- coding: utf-8 -*-

# Base Imports
import logging
import hashlib


## ServiceGatewayMiddleware
# This base class is for middleware that must be executed before or after a remote service method.
class ServiceGatewayMiddleware(object):

    """ Abstract class representing a piece of middleware that can hook into the service RPC request flow. """

    debug = False
    opts = {}
    config = {}

    def __init__(self, debug=False, config={}, opts={}):

        """ Take in config, whether we're in debug mode or not, and 'opts' (runtime config overrides). """

        self.debug = debug
        self.config = config
        self.opts = opts

    def __call__(self, request, reponse):

        """ Default to NotImplemented. """

        raise NotImplemented


# Middleware for monitoring individual and aggregate request statistics
class MonitoringMiddleware(ServiceGatewayMiddleware):

    """ Middleware for monitoring and reporting errors or auth failures. """

    def before_request(self, service, request, response):
        return (service, request, response)

    def after_request(self, service, request, response):
        return (service, request, response)


# Async Middleware for intercepting responses and returning them via Channel API
class AsyncPushMiddleware(ServiceGatewayMiddleware):

    """ Middleware for intercepting an asynchronous response from an API method. """

    def after_request(self, service, request, response):
        return (service, request, response)


# Middleware for recording monitored data to datastore or memcache
class RecordingMiddleware(ServiceGatewayMiddleware):

    """ Middleware for recording individual or aggregate information about remote service request load. """

    def before_request(self, service, request, response):
        return (service, request, response)


# Middleware for caching response messages & raw JSON responses
class CachingMiddleware(ServiceGatewayMiddleware):

    """ Middleware for holding onto data so it can be retrieved faster. """

    key = None
    ttl = None
    profile = None

    def generateKey(self, service, request, localize=False):

        """ Generate a hash representing the current request, suitable for use as a cache key. """

        # Add service class, request URI, method and body
        request_descriptor = [service.__repr__(), request.uri, request.method, request.body]

        # Add GET and POST vars if they exist
        if len(request.GET) > 0:
            request_descriptor.append(str(request.GET))  # Add getvars
        if len(request.POST) > 0:
            request_descriptor.append(str(request.POST))  # Add postvars

        return hashlib.sha256(reduce(lambda x, y: x + ':::' + y, request_descriptor)).hexdigest()

    def before_request(self, service, request, response):

        """ Generate a key before the request is fulfilled, check for existence in the cache, and return if available. """

        # @TODO: Clean up this file's logging...
        if 'caching' in service.config.get('service').get('config', []):
            self.profile = self.config['middleware_config']['caching']['profiles'][service.config['service']['config']['caching']]

            if self.profile['activate']['internal'] is True:
                self.key = self.generateKey(service, request, self.profile.get('localize', False))
                service._setstate('cache_key', self.key)

        return (service, request, response)

    def after_request(self, service, request, response):

        """ Store the request in the cache for later return. """

        pass


# Middleware for authenticating a remote client
class AuthenticationMiddleware(ServiceGatewayMiddleware):

    """ Middleware for enforcing the policy that a user (maybe only admins) must be authenticated. """

    def before_request(self, service, request, response):

        logging.info('SERVICE: ' + str(service))
        logging.info('REQUEST_TOKEN: ' + str(request.GET.get('token', '_NOTOKEN_')))

        return (service, request, response)


# Middleware for authorizing a remote client
class AuthorizationMiddleware(ServiceGatewayMiddleware):

    """ Middleware for enforcing the policy that a user must be part of a group or have a certain privilege. """

    def before_request(self, service, request, response):

        return (service, request, response)
