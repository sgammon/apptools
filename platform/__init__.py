# -*- coding: utf-8 -*-

'''

AppTools Platform

Enables AppTools to run on any platform supporting WSGI, with specific enhancements
for each one that can be identified in the environment.

-sam (<sam@momentum.io>)

'''

import config
import webapp2

from apptools.util import debug
from apptools.util import _loadModule

logging = debug.AppToolsLogger('apptools.platform')


## Platform
# Represents a group of features/hooks/utils that can be used as a platform to run AppTools.
class Platform(object):

    ''' Specifies a platform that AppTools can sit upon. '''

    pass


## PlatformInjector
# Represents a shortcut to a system/platform API, library, util or service.
class PlatformBridge(object):

    ''' Specifies a bridge between components of AppTools and a Platform feature. '''

    @webapp2.cached_property
    def logging(self):

        ''' Named log pipe. '''

        global logging
        return logging.extend(path='bridge', name=self.__class__.__name__)

    def lazyload(self, module):

        ''' Lazy load a module, or return False if it cannot be found/imported. '''

        try:
            module = _loadModule(module)
        except ImportError:
            self.logging.warning('Could not resolve shortcutted module "' + module + '". Encountered ImportError, returning False.')
            if config.debug:
                raise
            return False
        else:
            return module
