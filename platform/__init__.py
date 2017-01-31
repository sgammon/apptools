# -*- coding: utf-8 -*-

'''

    apptools platforms

    enables AppTools to run on any platform supporting WSGI, with specific enhancements
    for each one that can be identified in the environment.

    :author: Sam Gammon <sam@momentum.io>
    :copyright: (c) momentum labs, 2013
    :license: The inspection, use, distribution, modification or implementation
              of this source code is governed by a private license - all rights
              are reserved by the Authors (collectively, "momentum labs, ltd")
              and held under relevant California and US Federal Copyright laws.
              For full details, see ``LICENSE.md`` at the root of this project.
              Continued inspection of this source code demands agreement with
              the included license and explicitly means acceptance to these terms.

'''


# stdlib
import sys

# 3rd party
import webapp2

# Appconfig
try:
    import config; _APPCONFIG = True
except ImportError:
    _APPCONFIG = False

    # build fake config
    class FakeConfig(object):
        debug = True
        config = {'debug': True}

    config = FakeConfig()

# apptools util
from apptools.util import debug
from apptools.util import _loadModule


## Globals
logging = debug.AppToolsLogger('apptools.platform')


def _lazyloader(self, module):

    ''' Lazy load a module, or return False if it cannot be found/imported. '''

    if not config.debug:
        if module in sys.modules:
            return sys.modules[module]
    try:
        module = _loadModule(module)

    except ImportError:
        self.logging.warning('Could not resolve shortcutted module "' + str(module) + '". Encountered ImportError, assigning to empty DictProxy.')
        if config.debug:
            raise

    return module


## Platform
# Represents a group of features/hooks/utils that can be used as a platform to run AppTools.
class Platform(object):

    ''' Specifies a platform that AppTools can sit upon. '''

    @webapp2.cached_property
    def logging(self):

        ''' Named log pipe. '''

        global logging
        return logging.extend(path='bridge', name=self.__class__.__name__)

    lazyload = _lazyloader


## PlatformInjector
# Represents a shortcut to a system/platform API, library, util or service.
class PlatformBridge(object):

    ''' Specifies a bridge between components of AppTools and a Platform feature. '''

    @webapp2.cached_property
    def logging(self):

        ''' Named log pipe. '''

        global logging
        return logging.extend(path='bridge', name=self.__class__.__name__)

    lazyload = _lazyloader