# -*- coding: utf-8 -*-
import os
import config as sysconfig

from apptools.util import _loadModule
from apptools.util.debug import AppToolsLogger

logging = AppToolsLogger('core.PlatformInjector')


class PlatformInjector(type):

    ''' Resolves platforms supported by the current environment, and injects them into AppTools Core. '''

    # Platform Info
    adapters = {}
    platforms = []

    def __new__(cls, target):

        ''' Take stock of the platforms installed, then inject proper stuff into the target class. '''

        global logging

        config = sysconfig.config.get('apptools.system.platform')
        environ = os.environ

        ## Consider installed platforms
        for platform in config.get('installed_platforms', []):
            try:

                # Import adapter if we don't have it yet
                if platform.get('path') not in cls.adapters.keys():
                    platform_adapter = _loadModule(('.'.join(platform.get('path').split('.')[0:-1]), platform.get('path').split('.')[-1]))
                    cls.adapters[platform.get('path')] = platform_adapter
                else:
                    platform_adapter = cls.adapters.get(platform.get('path'))

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

                # Add to the installed platforms list, for later injection via __call__
                cls.platforms.append(platform)
        return cls.inject(target)

    @classmethod
    def inject(cls, target):

        ''' Take the target class and inject properties according to enabled platforms + features. '''

        ## Check for appropriate feature containers
        if not hasattr(target, 'platforms'):
            target.platforms = []
        if not hasattr(target, 'context_injectors'):
            target.context_injectors = []

        ## Install each platform
        for platform in cls.platforms:

            # Assign shortcut properties
            if hasattr(platform['adapter'], 'shortcut_exports'):
                for name, shortcut in platform['adapter'].shortcut_exports():
                    setattr(target, name, shortcut)

            # Add template context injectors
            if hasattr(platform['adapter'], 'template_context'):
                target.context_injectors.append(platform['adapter'].template_context())

            # Add the platform as installed
            target.platforms.append(platform['adapter'])

        ## Done! Return prepped Platform injectee
        return target
