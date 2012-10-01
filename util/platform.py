# -*- coding: utf-8 -*-

'''

Util: Platform

Resolves supported/installed Platforms and provides PlatformInjector, which can be used
to install dependencies into provided classes at runtime.

-sam (<sam@momentum.io>)

'''

import os

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
    adapters = {}
    platforms = []

    def __new__(cls, target):

        ''' Configure an injection sequence. '''

        cls.discover()
        return cls.inject(target)

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
        config = sysconfig.config.get('apptools.system.platform', {})

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
                        assert platform_adapter.check_environment(environ, sysconfig) == True

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

            return cls

    @classmethod
    def inject(cls, target):

        ''' Take the target class and inject properties according to enabled platforms + features. '''

        global logging
        global _adapters
        global _platforms

        ## Check for appropriate feature containers
        if not hasattr(target, 'platforms'):
            target.platforms = []
        if not hasattr(target, 'context_injectors'):
            target.context_injectors = []

        ## Install each platform
        for platform in _platforms:

            # Consider config shortcuts
            try:

                config_s = getattr(platform['adapter'], 'config_shortcuts')
                if not isinstance(config_s, list):
                    config_s = config_s()

                target.injected_config = []
                for name, shortcut in config_s:
                    if hasattr(target, name):
                        logging.warning('Platform config shortcut "' + name + '" on platform "' + str(platform) + '" already exists on the target injectee. Overwriting.')
                    try:
                        setattr(target, name, shortcut)
                    except Exception, e:
                        logging.warning('Platform config shortcut injection sequence for shortcut "' + name + '" on platform "' + str(platform) + '" encountered an unhandled exception: "' + str(e) + '".')
                        if sysconfig.debug:
                            raise
                        else:
                            continue
                    else:
                        target.injected_config.append((name, shortcut))

            except Exception:
                pass

            # Consider shortcut exports
            try:

                shortcuts = getattr(platform['adapter'], 'shortcut_exports')
                if not isinstance(shortcuts, list):
                    shortcuts = shortcuts()

                target.injected_shortcuts = []
                for name, shortcut in shortcuts:
                    if hasattr(target, name):
                        logging.warning('Platform config shortcut "' + name + '" on platform "' + str(platform) + '" already exists on the target injectee. Overwriting.')
                    try:
                        setattr(target, name, shortcut)
                    except Exception, e:
                        logging.warning('Platform config shortcut injection sequence for shortcut "' + name + '" on platform "' + str(platform) + '" encountered an unhandled exception: "' + str(e) + '".')
                        if sysconfig.debug:
                            raise
                        else:
                            continue
                    else:
                        target.injected_shortcuts.append((name, shortcut))

            except Exception:
                pass

            # Add template context injectors
            if hasattr(platform['adapter'], 'template_context'):
                target.context_injectors.append(platform['adapter'].template_context)

            # Add the platform as installed
            target.platforms.append(platform['adapter'])

        ## Done! Return prepped Platform injectee
        return target
