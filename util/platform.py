# -*- coding: utf-8 -*-

'''

Util: Platform

Resolves supported/installed Platforms and provides PlatformInjector, which can be used
to install dependencies into provided classes at runtime.

-sam (<sam@momentum.io>)

'''

import os
import webapp2

import config as sysconfig

from apptools.util import debug
from apptools.util import _loadModule

_adapters = []
_platforms = []

logging = debug.AppToolsLogger('core.util.platform')


## PlatformInjector
# This class injects dependencies through Python's decorator syntax (usage: @platform.PlatformInjector(config=values, go=here))
class PlatformInjector(object):

    ''' Resolves platforms supported by the current environment, and injects them into AppTools Core. '''

    # Platform Info
    config = {}
    adapters = {}
    platforms = []

    def __new__(self, shortcuts=False, config=False, context=False):

        ''' Configure an injection sequence. '''

        self.config['shortcuts'] = shortcuts
        self.config['config'] = config
        self.config['context'] = context

        return self.factory

    @webapp2.cached_property
    def logging(self):

        ''' Named log pipe. '''

        global logging
        return logging.extend(name='PlatformInjector')

    @classmethod
    def discover(cls):

        ''' Discover installed platforms, cache them globally. '''

        # Globals
        global logging
        global _adapters
        global _platforms

        # Setup environment
        adapters = {}
        platforms = []
        environ = os.environ
        config = sysconfig.config.get('apptools.system.platform')

        # If we have everything cached, just return it
        if len(_adapters) > 0 and len(_platforms) > 0:
            adapters = _adapters
            platforms = _platforms

            return platforms, adapters

        # Build our list of platforms/adapters manually
        else:

            # Consider installed platforms
            for platform in config.get('installed_platforms', []):
                try:

                    # Import adapter if we don't have it yet
                    if platform.get('path') not in adapters.keys():
                        platform_adapter = _loadModule(('.'.join(platform.get('path').split('.')[0:-1]), platform.get('path').split('.')[-1]))
                        adapters[platform.get('path')] = platform_adapter
                    else:
                        platform_adapter = adapters.get(platform.get('path'))

                    # Check if the platform is compatible
                    if hasattr(platform_adapter, 'check_environment'):
                        assert platform_adapter.check_environment(environ, config) == True

                # Couldn't find the platform...
                except ImportError:
                    if sysconfig.debug:
                        logging.error('Platform "%s" is mentioned in config but could not be found at the configured path ("%s").' % (platform.get('name', 'UnkownPlatform'), platform.get('path')))
                    continue

                # Platform wasn't compatible...
                except AssertionError:
                    if sysconfig.debug:
                        logging.debug('Platform "%s" was tested and is not compatible with this environment. Continuing.' % str(platform.get('name', 'UnknownPlatform')))
                    continue

                # Platform is A-OK
                else:
                    # Create it, so it has a chance to init
                    platform['adapter'] = platform_adapter()
                    platforms.append(platform)

            # Set to globals
            _adapters = dict(adapters.items()[:])
            _platforms = platforms[:]

            return platforms, adapters

    def factory(self, target, inject=True):

        ''' Take stock of the platforms installed, then inject proper stuff into the target class. '''

        global _adapters
        global _platforms

        ## Consider installed platforms
        if (len(_adapters) == 0 and len(_platforms) == 0) and (len(self.adapters) == 0 and len(self.platforms) == 0):
            self.platforms, self.adapters = self.discover()

        elif len(self.adapters) == 0 and len(self.platforms) == 0:
            self.platforms, self.adapters = _platforms, _adapters

        if inject:
            return self.inject(target, self)
        else:
            return self

    @classmethod
    def inject(cls, target, config=None):

        ''' Take the target class and inject properties according to enabled platforms + features. '''

        global logging
        global _adapters
        global _platforms

        ## We're running statically...
        if config is None:
            config = object()
            config.adapters = _adapters
            config.platforms = _platforms
            config.logging = logging
            config.shortcuts = True
            config.context = True
            config.config = True
        else:
            config.shortcuts = config.config.get('shortcuts')
            config.context = config.config.get('context')
            config.config = config.config.get('config')

        ## Check for appropriate feature containers
        if not hasattr(target, 'platforms'):
            target.platforms = []
        if not hasattr(target, 'context_injectors'):
            target.context_injectors = []

        ## Install each platform
        for platform in config.platforms:

            # Add config shortcuts
            shortcut_types = (('config_shortcuts', config.config), ('shortcut_exports', config.shortcuts))

            # Assign shortcut properties
            for shortcut_type in filter(lambda x: x[1] is not False, shortcut_types):
                if hasattr(platform['adapter'], shortcut_type):
                    try:
                        # Retrieve it property-style first, in case it's a cached property
                        shortcuts = getattr(platform['adapter'], shortcut_type)

                        # If it's not a results list, it's a callable probably
                        if not isinstance(shortcuts, list):
                            shortcuts = shortcuts()

                        # Add each shortcut
                        for name, shortcut in shortcuts:
                            if hasattr(target, name):
                                config.logging.warning('Platform shortcut "' + name + '" on platform "' + platform + '" already exists on the target injectee. Overwriting.')
                            try:
                                setattr(target, name, shortcut)
                            except Exception, e:
                                config.logging.warning('Platform shortcut injection sequence for shortcut "' + name + '" on platform "' + platform + '" encountered unhandled exception of type "' + str(e) + '".')
                                if sysconfig.debug:
                                    raise
                                else:
                                    continue
                    except Exception, e:
                        config.logging.warning('Platform shortcut type "' + shortcut_type + '" could not be found/initialized/resolved on platform "' + platform + '" and encountered an unhandled exception of type "' + str(e) + '".')
                        if sysconfig.debug:
                            raise
                        else:
                            continue
                else:
                    continue

            # Add template context injectors
            if config.context and hasattr(platform['adapter'], 'template_context'):
                target.context_injectors.append(platform['adapter'].template_context)

            # Add the platform as installed
            target.platforms.append(platform['adapter'])

        ## Done! Return prepped Platform injectee
        return target
