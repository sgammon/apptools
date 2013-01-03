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
import os
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
            raise KeyError("Key '%s' does not exist on transport integration bus '%s'." % (key, self.__class__))


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

        return _logger.extend(name='UpstreamBridge')._setcondition(self._l9config.get('debug', False))


## FrontlineBridge
# This class bridges and proxies internal calls to L9AF frontline-specific code.
class FrontlineBridge(PlatformBridge, TransportBusManager):

    ''' Bridge to frontline-specific features. '''

    @webapp2.cached_property
    def config(self):

        ''' Named config pipe to frontline L9AF config. '''

        return config.config.get('.'.join([self.l9_config_path, self.frontline_config_key]), {})

    @webapp2.cached_property
    def logging(self):

        ''' Named logging pipe. '''

        return _logger.extend(name='FrontlineBridge')._setcondition(self._l9config.get('debug', False))


## ControllerBridge
# This class bridges and proxies internal calls to L9AF controller-specific code.
class ControllerBridge(PlatformBridge, TransportBusManager):

    ''' Bridge to controller-specific features. '''

    @webapp2.cached_property
    def config(self):

        ''' Named config pipe to controller L9AF config. '''

        return config.config.get('.'.join([self.l9_config_path, self.controller_config_key]), {})

    @webapp2.cached_property
    def logging(self):

        ''' Named logging pipe. '''

        return _logger.extend(name='ControllerBridge')._setcondition(self._l9config.get('debug', False))


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

    version = property(lambda self: self.lib.__version__, None)

    def __init__(self):

        ''' Lazy-load the AppFactory integration library. '''

        self.lib = self.lazyload('appfactory')
        self.appfactory = datastructures.DictProxy({
            self.upstream_config_key: UpstreamBridge(bus=self.lib.upstream),
            self.frontline_config_key: FrontlineBridge(bus=self.lib.frontline),
            self.controller_config_key: ControllerBridge(bus=self.lib.controller),
            'version': self.version
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
        enabled = config.config.get(cls.l9_config_path, {}).get('enabled', False)

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

            (''.join([self.upstream_config_key, 'Config']), self.appfactory.upstream.config),
            (''.join([self.frontline_config_key, 'Config']), self.appfactory.frontline.config),
            (''.join([self.controller_config_key, 'Config']), self.appfactory.controller.config)

        ]

    def _log_dispatch(self, data):

        ''' Save processed Layer9 data into memcache, for statistics gathering. '''

        self.logging.info('LOG DISPATCH CALLED: "%s".' % data)
        return data

    def pre_dispatch(self, handler):

        ''' Hook into apptools before dispatch is run, and modify the request if Frontline-added HTTP headers are present. '''

        # Try to detect appfactory headers, added from the frontline
        self.appfactory.frontline.sniff(handler)

        # Try to detect partial content requests, added from the upstream
        self.appfactory.upstream.sniff(handler)
        return

    def post_dispatch(self, handler, result):

        ''' Hook into apptools after dispatch has run, and read stats from the response to dump to memcache. '''

        # Consider asset headers for upstream
        result = self.appfactory.upstream.hint(handler, result)

        # Dump data to memcache
        data = []
        for i in [self.appfactory.frontline, self.appfactory.upstream, self.appfactory.controller]:
            data.append(i.dump(handler, result))

        self._log_dispatch(data)

        return result

    @webapp2.cached_property
    def template_context(self):

        ''' Inject AppFactory-specific tools. '''

        def inject(handler, context):
            if os.environ.get('APPFACTORY', False):
                context['util']['request']['geo'] = {}
                context['util']['instance'] = os.environ.get('XAF_INSTANCE', 'web-1')
                context['util']['software'] = os.environ.get('XAF_BACKEND', 'yoga-sandbox')
                context['util']['datacenter'] = os.environ.get('XAF_DATACENTER', 'usw-1-b')

                context['api'] = handler.api
                context['util']['api'] = handler.api
                context['util']['request']['hash'] = '__UNDEFINED__'
                context['util']['request']['namespace'] = '__UNDEFINED__'

            return context

        return inject
