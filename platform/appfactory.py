# -*- coding: utf-8 -*-

'''

Platform: AppFactory

Deep integration with momentum labs' Layer9 AppFactory platform. Exposes
and injects shortcuts to code that controls, parses, and mediates signals
between AppEngine and the individual AppFactory components: the Frontline,
Upstream and Controller layers.

-sam (<sam@momentum.io>)

'''

# Base Imports
import config
import webapp2

# Util Imports
from apptools.util import debug
from apptools.util import datastructures

# Platform Imports
from apptools.platform import Platform
from apptools.platform import PlatformBridge

# Mod Globals
_logger = debug.AppToolsLogger(path='apptools.platform.appfactory')


## TransportBusManager
# Provides bus management features to L9 layer bridges.
class TransportBusManager(object):

    ''' Mixes in bus management features to L9 bridge classes. '''

    def __init__(self, bus):

        ''' Accept a bus object at init, assign to self and proxy. '''

        self.bus = bus

    def __get__(self, instance, owner):

        ''' Return the bus upon descriptor access. '''

        return self.bus

    def __getattr__(self, key):

        ''' Proxy gets to the bus. '''

        if hasattr(self.bus, key):
            return getattr(self.bus, key)
        else:
            raise AttributeError('Key "%s" does not exist on transport integration bus "%s".' % (key, self.__class__))

    def __getitem__(self, key):

        ''' Proxy getitems to getattr. '''

        try:
            return getattr(self, key)

        except AttributeError:
            raise


## UpstreamBridge
# This class bridges and proxies internal calls to L9AF upstream-specific code.
class UpstreamBridge(PlatformBridge, TransportBusManager):

    ''' Bridge to upstream-specific features. '''

    @webapp2.cached_property
    def config(self):

        ''' Named config pipe to upstream L9AF config. '''

        return config.config.get('.'.join([self.l9_config_path, self.upstream_config_key]), {})

    @webapp2.cached_property
    def logging(self):

        ''' Named logging pipe. '''

        return _logger.extend(name='UpstreamBridge')._setcondition(self._l9config.get('logging', False))


## FrontlineBridge
# This class bridges and proxies internal calls to L9AF frontline-specific code.
class FrontlineBridge(PlatformBridge, TransportBusManager):

    ''' Bridge to frontline-specific features. '''

    @webapp2.cached_property
    def config(self):

        ''' Named config pipe to frontline L9AF config. '''

        return config.config.get('.'.join([self.l9_config_path, self.upstream_config_key]), {})

    @webapp2.cached_property
    def logging(self):

        ''' Named logging pipe. '''

        return _logger.extend(name='FrontlineBridge')._setcondition(self._l9config.get('logging', False))


## ControllerBridge
# This class bridges and proxies internal calls to L9AF controller-specific code.
class ControllerBridge(PlatformBridge, TransportBusManager):

    ''' Bridge to controller-specific features. '''

    @webapp2.cached_property
    def config(self):

        ''' Named config pipe to controller L9AF config. '''

        return config.config.get('.'.join([self.l9_config_path, self.upstream_config_key]), {})

    @webapp2.cached_property
    def logging(self):

        ''' Named logging pipe. '''

        return _logger.extend(name='ControllerBridge')._setcondition(self._l9config.get('logging', False))


## Layer9AppFactory
# This class provides AppFactory integration to AppTools.
class AppFactory(Platform):

    ''' Provider for integration with momentum's Layer9 AppFactory platform. '''

    # Main Config
    l9_config_path = 'layer9.appfactory'
    l9_header_prefix = 'X-AppFactory'

    # Config Keys
    upstream_config_key = 'upstream'
    frontline_config_key = 'frontline'
    controller_config_key = 'controller'

    def __init__(self):

        ''' Lazy-load the AppFactory integration library. '''

        self.lib = self.lazyload('appfactory')
        self.appfactory = datastructures.DictProxy({
            'upstream': UpstreamBridge(bus=self.lib.upstream),
            'frontline': FrontlineBridge(bus=self.lib.frontline),
            'controller': ControllerBridge(bus=self.lib.controller)
        })

    @webapp2.cached_property
    def logging(self):

        ''' Named logging pipe. '''

        return _logger.extend(name='AppFactory')._setcondition(self._l9config.get('logging', False))

    @webapp2.cached_property
    def _l9config(self):

        ''' Named config pipe to main L9AF config. '''

        return config.config.get(self.l9_config_path, {})

    @classmethod
    def check_environment(cls, environ, config):

        ''' Check config to see if AppFactory integration is enabled. '''

        _logger.info('Checking environment for AppFactory compatibility.')
        enabled = config.config.get(cls.l9_config_path).get('enabled', False)

        if enabled:
            _logger.info('AppFactory compatibility tests passed, integration enabled.')
        else:
            _logger.warning('AppFactory is not supported in the current environment or is not enabled.')

        return enabled

    @webapp2.cached_property
    def shortcut_exports(self):

        ''' Return shortcuts to AppFactory functionality. '''

        return [('appfactory', self.appfactory)]

    @webapp2.cached_property
    def config_shortcuts(self):

        return [

            ('upstreamConfig', self.appfactory.upstream.config),
            ('frontlineConfig', self.appfactory.frontline.config),
            ('controllerConfig', self.appfactory.controller.config)

        ]

    def pre_dispatch(self, handler):

        ''' Hook into apptools before dispatch is run, and modify the request if Frontline-added HTTP headers are present. '''

        # Try to detect appfactory headers, added from the frontline
        self.appfactory.frontline.sniff(handler)

    def post_dispatch(self, handler, result):

        ''' Hook into apptools after dispatch has run, and read stats from the response to dump to memcache. '''

        self.logging.info('RESPONSE DUMP:')
        self.logging.info(str(handler.response.headers))

        return result
