# -*- coding: utf-8 -*-

'''

Platform: Generic WSGI

Base platform functionality that is enabled in every supported environment.
Provides utils and shortcuts that should always be available in AppTools.

-sam (<sam@momentum.io>)

'''

import config
import webapp2

from apptools.platform import Platform
from apptools.platform import PlatformBridge


## AppToolsExtBridge
# This class provides shortcuts to AppTools extensions and APIs.
class AppToolsExtBridge(PlatformBridge):

    ''' Bridge to AppTools APIs and extensions. '''

    def __get__(self, instance, owner):

        ''' Offers shortcuts to installed AppTools APIs/extensions. '''

        # stubbed... for now (@TODO)
        return self


## AppToolsUtilBridge
# This class provides shortcuts to builtin/common 3rd party libraries.
class AppToolsUtilBridge(PlatformBridge):

    ''' Offers shortcuts to installed third-party libraries. '''

    def __get__(self, instance, owner):

        from apptools.util import _loadModule
        from apptools.util import datastructures

        # Return CallbackProxy to lazy-load module access
        return datastructures.CallbackProxy(_loadModule, {

            'timesince': ('apptools.util.timesince', 'timesince'),
            'byteconvert': ('apptools.util.byteconvert', 'humanize_bytes'),
            'httpagentparser': ('apptools.util.httpagentparser', 'detect')

        })


## GenericWSGI
# This Platform class provides base utilities, shortcuts, and config access for all environments.
class GenericWSGI(Platform):

    ''' Platform-specific features and exports for Google App Engine. '''

    ext = AppToolsExtBridge()
    util = AppToolsUtilBridge()

    @classmethod
    def check_environment(cls, environ, config):

        ''' Always enable generic environment. '''

        return True  # Always enable GenericWSGI

    @webapp2.cached_property
    def config(self):

        ''' Cached shortcut to global config. '''

        return config.config

    @webapp2.cached_property
    def _sysConfig(self):

        ''' Cached shortcut to system config. '''

        return self.config.get('apptools.system')

    @webapp2.cached_property
    def _globalServicesConfig(self):

        ''' Cached shortcut to global (AppTools) service config. '''

        return self.config.get('apptools.services')

    @webapp2.cached_property
    def _servicesConfig(self):

        ''' Cached shortcut to project services config. '''

        return self.config.get('apptools.project.services')

    @webapp2.cached_property
    def _projectConfig(self):

        ''' Cached shortcut to project config. '''

        return self.config.get(self.configPath)

    @webapp2.cached_property
    def _projectOutput(self):

        ''' Cached shortcut to project output config. '''

        return self.config.get('.'.join(self.configPath.split('.') + ['output']))

    @webapp2.cached_property
    def shortcut_exports(self):

        ''' Return shortcuts. '''

        return [

            # Lib, Ext & Util
            ('ext', self.ext), ('util', self.util),

            # Services, Messages & Models

        ]

    @webapp2.cached_property
    def config_shortcuts(self):

        ''' Return config shortcuts only. '''

        return [
            # Main Config
            ('config', self.config), ('_sysConfig', self._sysConfig),

            # Services Config
            ('_globalServicesConfig', self._globalServicesConfig), ('_servicesConfig', self._servicesConfig),

            # Project Config
            ('_projectConfig', self._projectConfig), ('_projectOutput', self._projectOutput)
        ]

    @webapp2.cached_property
    def template_context(self):

        ''' Inject generic + apptools stuff into the template context. '''

        def inject(handler, context):

            ''' Add AppTools-related stuff. '''

            context['asset'] = {  # Bridge to the Assets API

                'url': handler.get_asset,  # generate a URL for an asset (low level method)
                'image': handler.get_img_asset,  # generate a URL for an image asset
                'style': handler.get_style_asset,  # generate a URL for a stylesheet asset
                'script': handler.get_script_asset  # generate a URL for a javascript asset

            }

            context['util']['config'] = {  # Main Config

                    'get': config.config.get,
                    'debug': config.debug,
                    'system': self._sysConfig,
                    'project': self._projectConfig,

                    'services': {
                        'global': self._globalServicesConfig,
                        'project': self._servicesConfig
                    }

            }

            context['converters']['timesince'] = self.util.timesince  # Util library for "15 minutes ago"-type text from datetimes
            context['converters']['byteconvert'] = self.util.byteconvert  # Util library for formatting data storage amounts

            return context

        return inject
