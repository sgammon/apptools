# -*- coding: utf-8 -*-
from apptools.platform import Platform
from apptools.platform import PlatformBridge


class AppToolsExtBridge(PlatformBridge):

    def __get__(self, instance, owner):

        ''' Offers shortcuts to installed AppTools APIs/extensions. '''

        return self


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


class GenericWSGI(Platform):

    ''' Platform-specific features and exports for Google App Engine. '''

    ext = AppToolsExtBridge()
    util = AppToolsUtilBridge()

    @classmethod
    def check_environment(cls, environ, config):

        ''' Always enable generic environment. '''

        return True  # always enable generic environment

    def shortcut_exports(self):

        ''' Return shortcuts. '''

        return [('ext', self.ext), ('util', self.util)]

    def template_context(self):

        ''' Inject generic + apptools stuff into the template context. '''

        def inject(handler, context):

            ''' Nothing yet, lol. '''

            return context

        return inject
