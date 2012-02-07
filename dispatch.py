# -*- coding: utf-8 -*-

## WSGI Gateway will go here eventually
import webapp2
from google.appengine.api import users


##### Basic Handlers #####
class NoOperationHandler(webapp2.RequestHandler):

    ''' Does nothing. '''

    def noop(self):
        self.response.write('NO-OP')
        self.error(404)

    def get(self, *args, **kwargs):
        return self.noop()

    def post(self, *args, **kwargs):
        return self.noop()


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
_sitemap_app = webapp2.WSGIApplication([webapp2.Route('/_app/sitemap.*', SitemapHandler, name='sitemap-handler')])
_appcache_app = webapp2.WSGIApplication([webapp2.Route('/_app/manifest.*', CacheManifestHandler, name='cache-manifest-handler')])


## WSGI/CGI Bridge
def _run(cbk, environ, start_response):
    global _noop_app
    if cbk is None:
        cbk = _noop_app
    if environ is not None and start_response is not None:
        cbk(environ, start_response)
    else:
        cbk.run()


## Builtin Extension Bridges
def admin(environ=None, start_response=None):
    if not users.get_current_user() or not users.is_current_user_admin():
        _run(None, environ, start_response)  # return no-op if they aren't logged in or aren't admin
    else:
        _run(None, environ, start_response)  # replace with actual control panel


def sitemap(environ=None, start_response=None):
    _run(_sitemap_app, environ, start_response)


def appcache(environ=None, start_response=None):
    _run(_appcache_app, environ, start_response)


## Extension exports
_installed_extensions = {
    'admin': admin,
    'sitemap': sitemap,
    'appcache': appcache
}
