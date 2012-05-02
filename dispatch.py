# -*- coding: utf-8 -*-

'''

AppTools Dispatch

Used for dispatching URLs that are internal to AppTools, and routing
requests to the user's app.

-sam (<sam@momentum.io>)

'''

import webapp2


##### Basic Handlers #####
class NoOperationHandler(webapp2.RequestHandler):

    ''' Does nothing. '''

    def noop(self):
        self.response.write('NO-OP')
        self.error(404)

    def get(self, *args, **kwargs):

        ''' Pass to NO-OP handler and 404. '''

        return self.noop()

    def post(self, *args, **kwargs):

        ''' Pass to NO-OP handler and 404. '''

        return self.noop()


class AppAdminHandler(webapp2.RequestHandler):

    ''' Provides a clean admin panel that comes standard with your app. '''

    def get(self):
        self.response.write('Admin panel coming soon.')


class SitemapHandler(webapp2.RequestHandler):

    ''' Automatically generates a sitemap in proper XML format. '''

    def get(self):
        self.response.write('Sitemaps coming soon.')


class CacheManifestHandler(webapp2.RequestHandler):

    ''' Automatically generates an HTML5 AppCache manifest in proper format. '''

    def get(self):
        self.response.write('Appcache manifests coming soon')


## WSGIApp Mappings
_noop_app = webapp2.WSGIApplication([webapp2.Route('/.*', NoOperationHandler, name='no-op-handler')])
_admin_app = webapp2.WSGIApplication([webapp2.Route('/_app/manage.*', AppAdminHandler, name='admin-handler-root')])
_sitemap_app = webapp2.WSGIApplication([webapp2.Route('/_app/sitemap.*', SitemapHandler, name='sitemap-handler')])
_appcache_app = webapp2.WSGIApplication([webapp2.Route('/_app/manifest.*', CacheManifestHandler, name='cache-manifest-handler')])


## Get builtin apps
def get_builtin_apps():

    ''' Return a list of builtin WSGI applications. This should NOT include _noop_app, which is only present for utility/fallback. '''

    return [_admin_app, _sitemap_app, _appcache_app]


## WSGI/CGI Bridge
def _run(cbk, environ, start_response):

    ''' Run an app, via CGI or WSGI if possible. '''

    global _noop_app
    if cbk is None:
        cbk = _noop_app
    if environ is not None and start_response is not None:
        cbk(environ, start_response)
    else:
        cbk.run()


## Builtin Extension Bridges
def admin(environ=None, start_response=None):

    ''' Run the admin panel app. '''

    global _admin_app
    from google.appengine.api import users
    if not users.get_current_user() or not users.is_current_user_admin():
        _run(None, environ, start_response)  # return no-op if they aren't logged in or aren't admin
    else:
        _run(_admin_app, environ, start_response)  # replace with actual control panel


def sitemap(environ=None, start_response=None):

    ''' Run the sitemap generation app. '''

    _run(_sitemap_app, environ, start_response)


def appcache(environ=None, start_response=None):

    ''' Run the appcache manifest generation app. '''

    _run(_appcache_app, environ, start_response)


## Extension exports
_installed_extensions = {
    'admin': admin,
    'sitemap': sitemap,
    'appcache': appcache
}
