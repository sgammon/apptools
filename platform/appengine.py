# -*- coding: utf-8 -*-

'''

Platform: Google App Engine

Enables shortcuts, libraries and other utilities that are specific to App Engine.
Also provides a template context injector for GAE-specific request info/environment.

-sam (<sam@momentum.io>)

'''

import webapp2

from apptools.util import datastructures

from apptools.platform import Platform
from apptools.platform import PlatformBridge


## GAELibBridge
# Offers shortcutted access to common/useful GAE libs.
class GAELibBridge(PlatformBridge):

    ''' Offers shortcuts to common App Engine libraries. '''

    def __get__(self, instance, owner):

        # Return a CallbackProxy to lazy-load the requested module
        return datastructures.CallbackProxy(self.lazyload, {

            'protorpc': 'protorpc',
            'pipelines': 'pipeline',
            'mapreduce': 'mapreduce'

        })


## GAEAPIBridge
# Offers shortcutted and unified access to all GAE APIs.
class GAEAPIBridge(PlatformBridge):

    ''' Offers shortcuts to App Engine APIs. '''

    def __get__(self, instance, owner):

        ## Return a CallbackProxy to lazy-load the requested module
        return datastructures.CallbackProxy(self.lazyload, {

            # Database APIs
            'db': ('google.appengine.ext', 'db'),
            'ndb': ('google.appengine.ext', 'ndb'),
            'sql': ('google.appengine.api', 'rdbms'),
            'rdbms': ('google.appengine.api', 'rdbms'),

            # Storage APIs
            'blob': ('google.appengine.ext', 'blobstore'),
            'files': ('google.appengine.api', 'files'),
            'blobstore': ('google.appengine.ext', 'blobstore'),

            # Communication APIs
            'xmpp': ('google.appengine.api', 'xmpp'),
            'mail': ('google.appengine.api', 'mail'),
            'channel': ('google.appengine.api', 'channel'),

            # Low-Level APIs
            'quota': ('google.appengine.api', 'quota'),
            'capabilities': ('google.appengine.api', 'capabilities'),

            # Auth APIs
            'oauth': ('google.appengine.api', 'oauth'),
            'users': ('google.appengine.api', 'users'),

            # Search/Indexing APIs
            'search': ('google.appengine.api', 'search'),
            'matcher': ('google.appengine.api', 'prospective_search'),
            'prospective_search': ('google.appengine.api', 'prospective_search'),

            # Media APIs
            'images': ('google.appengine.api', 'images'),
            'conversion': ('google.appengine.api', 'conversion'),

            # Infrastructure APIs
            'backends': ('google.appengine.api', 'backends'),
            'memcache': ('google.appengine.api', 'memcache'),
            'urlfetch': ('google.appengine.api', 'urlfetch'),
            'identity': ('google.appengine.api', 'app_identity'),
            'taskqueue': ('google.appengine.api', 'taskqueue'),
            'logservice': ('google.appengine.api', 'logservice'),
            'app_identity': ('google.appengine.api', 'app_identity'),
            'multitenancy': ('google.appengine.api', 'namespace_manager'),

            # Other APIs
            'zipserve': ('google.appengine.ext', 'zipserve'),
            'deferred': ('google.appengine.ext', 'deferred'),
            'mapreduce': ('google.appengine.ext', 'mapreduce')

        })


## GoogleAppEngine
# Ties together features, libraries, shortcuts and config access for operating AppTools on Google App Engine.
class GoogleAppEngine(Platform):

    ''' Platform-specific features and exports for Google App Engine. '''

    api = GAEAPIBridge()
    lib = GAELibBridge()

    @classmethod
    def check_environment(cls, environ, config):

        ''' Check the environment and see if we're running on GAE. '''

        try:
            from google.appengine.ext import ndb
        except ImportError as e:
            return False
        return True

    @webapp2.cached_property
    def shortcut_exports(self):

        ''' Return shortcuts. '''

        return [('api', self.api), ('lib', self.lib)]

    @webapp2.cached_property
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
