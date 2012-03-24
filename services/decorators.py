# -*- coding: utf-8 -*-

# Base Imports
import config

# Shortcuts
from apptools.core import _libbridge
from apptools.core import _apibridge
from apptools.core import _extbridge
from apptools.core import _utilbridge

# Datastructures
from apptools.util.datastructures import DictProxy


## RemoteMethodDecorator
# This base class is for decorators that annotate remote service methods
class RemoteMethodDecorator(object):

    """ Indicates a class that can be used to decorate a remote method (a function on a class that responds to a remote API request). """

    args = None
    kwargs = None
    request = None
    service = None
    callback = None

    lib = _libbridge
    api = _apibridge
    ext = _extbridge
    util = _utilbridge

    def __init__(self, *args, **kwargs):

        """ Take in positional and keyword arguments when it is used as a decorator. """

        self.args = args
        self.kwargs = kwargs

    def __call__(self, fn):

        """ When the target remote method is called... """

        def wrapped(service_obj, request):

            """ Redirect the function call to our decorator's execute call (this enables us to do things like caching inside a decorator, by hijacking the remote method call and injecting a return value from the cache)... """

            self.callback = fn
            self.service = service_obj
            self.request = request

            for n in set(dir(fn)) - set(dir(self)):
                setattr(self, n, getattr(fn, n))

            return self.execute(*self.args, **self.kwargs)  # <-- redirect to our execute()

        return wrapped

    def execute(self, *args, **kwargs):

        """ Default decorator execution case: run the remote method (or, pass it down the chain to the next decorator) and return the result. """

        return self.execute_remote()

    def execute_remote(self):

        """ Shortcut to execute the remote method/next decorator and return the result. """

        return self.callback(self.service, self.request)

    def __repr__(self):

        """ Pleasant for debugging. """

        return self.callback


## Auditing Flags

# Monitor individual and aggregate request data, and log to datastore or memcache
class Monitor(RemoteMethodDecorator):

    """ Log remote requests when they happen, and optionally store stats/usage per API consumer in the datastore and memcache. """

    def execute(self, *args, **kwargs):
        return self.execute_remote()


# Set debug to true or false in the scope of a single remote method
class Debug(RemoteMethodDecorator):

    """ Set debug mode to true or false for a remote method. Adds extra debug flags to the response envelope and ups the logging level. """

    def execute(self):
        config.debug = True
        result = self.execute_remote()
        config.debug = False
        return result


# Set the minimum log severity in the scope of a single remote method
class LogLevel(RemoteMethodDecorator):

    """ Manually set the logging level for a remote service method. """

    def execute(self):
        return self.execute_remote()


## Caching Flags

# Specify a method's caching policy for all caching layers.
class Cacheable(RemoteMethodDecorator):

    """ Indicate that the response from a remote method is cacheable locally on the browser side. """

    def execute(self, *args, **kwargs):
        return self.execute_remote()


# Specify a method's caching policy for threadlocal/global layers.
class LocalCacheable(RemoteMethodDecorator):

    """ Indicate that the response from a remote method is cacheable in instance memory (fastcache). """

    def execute(self):
        return self.execute_remote()


# Specify a method's caching policy for memcaching.
class MemCacheable(RemoteMethodDecorator):

    """ Indicate that the response from a remote method is memcacheable. """

    def execute(self):
        return self.execute_remote()


## Security Flags

# Specify that a remote service client cannot be on a blacklist in order to execute successfully.
class Blacklist(RemoteMethodDecorator):

    """ Indicate that a remote method must be matched against a blacklist. """

    def execute(self, *args, **kwargs):
        return self.execute_remote()


# Specify that a remote service client must be on a whitelist in order to execute successfully.
class Whitelist(RemoteMethodDecorator):

    """ Indicate that a remote method must be matched against a whitelist. """

    def execute(self, *args, **kwargs):
        return self.execute_remote()


# Specify that a remote service client must authorize via an ACL or other grouping of users.
class Authorize(RemoteMethodDecorator):

    """ Indicate that a remote method requires authorization. """

    def execute(self, *args, **kwargs):
        return self.execute_remote()


# Specify that a remote service client must authenticate before executing remote methods.
class Authenticate(RemoteMethodDecorator):

    """ Indicate that a remote method requires authentication. """

    def execute(self):
        return self.execute_remote()


# Specify that a remote service method can be run by AppEngine-registered admins only.
class AdminOnly(RemoteMethodDecorator):

    """ Indicate that a remote method requires an admin to be logged in. """

    def execute(self):
        if self.api.users.is_current_user_admin():
            return self.execute_remote()
        else:
            raise Exception()


## Decorator shortcuts

# Audit decorators
audit = DictProxy({

    'Monitor': Monitor,
    'Debug': Debug,
    'LogLevel': LogLevel,

})

# Caching decorators
caching = DictProxy({

    'Cacheable': Cacheable,
    'LocalCacheable': LocalCacheable,
    'MemCacheable': MemCacheable,

})

# Security decorators
security = DictProxy({

    'Authorize': Authorize,
    'Authenticate': Authenticate,
    'AdminOnly': AdminOnly

})
