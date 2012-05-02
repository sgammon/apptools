# -*- coding: utf-8 -*-
from apptools.platform import Platform
from apptools.platform import PlatformBridge


class GAEAPIBridge(PlatformBridge):

    ''' Offers shortcuts to App Engine APIs. '''

    def __get__(self, instance, owner):

        from apptools.util import _loadModule
        from apptools.util import datastructures

        return datastructures.CallbackProxy(_loadModule, {

            'pipelines': 'pipeline',
            'mapreduce': 'mapreduce',
            'db': ('google.appengine.ext', 'db'),
            'ndb': ('google.appengine.ext', 'ndb'),
            'xmpp': ('google.appengine.api', 'xmpp'),
            'mail': ('google.appengine.api', 'mail'),
            'quota': ('google.appengine.api', 'quota'),
            'oauth': ('google.appengine.api', 'oauth'),
            'users': ('google.appengine.api', 'users'),
            'files': ('google.appengine.api', 'files'),
            'search': ('google.appengine.api', 'search'),
            'images': ('google.appengine.api', 'images'),
            'channel': ('google.appengine.api', 'channel'),
            'matcher': ('google.appengine.api', 'prospective_search'),
            'backends': ('google.appengine.api', 'backends'),
            'memcache': ('google.appengine.api', 'memcache'),
            'urlfetch': ('google.appengine.api', 'urlfetch'),
            'identity': ('google.appengine.api', 'app_identity'),
            'blobstore': ('google.appengine.ext', 'blobstore'),
            'taskqueue': ('google.appengine.api', 'taskqueue'),
            'logservice': ('google.appengine.api', 'logservice'),
            'conversion': ('google.appengine.api', 'conversion'),
            'capabilities': ('google.appengine.api', 'capabilities'),
            'multitenancy': ('google.appengine.api', 'namespace_manager'),
            'app_identity': ('google.appengine.api', 'app_identity'),
            'prospective_search': ('google.appengine.api', 'prospective_search')

        })


class GoogleAppEngine(Platform):

    ''' Platform-specific features and exports for Google App Engine. '''

    api = GAEAPIBridge()

    @classmethod
    def check_environment(cls, environ, config):

        ''' Check the environment and see if we're running on GAE. '''

        return True  # no other environments supported yet

    def shortcut_exports(self):

        ''' Return shortcuts. '''

        return [('api', self.api)]

    def template_context(self):

        ''' Inject GAE-specific tools into the template context. '''

        def inject(handler, context):
            ## Util
            context['util']['request']['geo'] = {  # Geo Information

              'latlong': handler.request.environ.get('HTTP_X_APPENGINE_CITYLATLONG'),
              'country': handler.request.environ.get('HTTP_X_APPENGINE_COUNTRY'),
              'region': handler.request.environ.get('HTTP_X_APPENGINE_REGION'),
              'city': handler.request.environ.get('HTTP_X_APPENGINE_CITY')

            }

            context['util']['appengine'] = {  # App Information

                'instance': handler.request.environ.get('INSTANCE_ID'),
                'current_version': handler.request.environ.get('CURRENT_VERSION_ID'),
                'datacenter': handler.request.environ.get('DATACENTER'),
                'software': handler.request.environ.get('SERVER_SOFTWARE'),
                'backend': handler.api.backends.get_backend()

            }

            context['api'] = handler.api
            context['util']['api'] = handler.api
            context['util']['request']['hash'] = handler.request.environ.get('REQUEST_ID_HASH')  # request hash (from Google)
            context['util']['request']['namespace'] = handler.api.multitenancy.get_namespace()  # current namespace

            return context

        return inject
