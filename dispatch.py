# -*- coding: utf-8 -*-

'''

    apptools dispatch

    used for dispatching URLs that are internal to AppTools, and routing
    requests to the user's app.

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
import os
import config
import inspect
import logging

# 3rd party
import webapp2

try:
    import endpoints
except ImportError as e:
    endpoints = False

rule_builders = []
installed_apps = config.config.get('webapp2', {}).get('apps_installed', [])
if len(installed_apps) == 0:
    installed_apps.append(None)
for app in installed_apps:
    try:
        if app is not None:
            rule_builders.append(webapp2.import_string('.'.join([app, 'routing', 'get_rules'])))
        else:
            rule_builders.append(webapp2.import_string('.'.join(['routing', 'get_rules'])))
    except (ImportError, webapp2.ImportStringError):
        continue

from apptools import core
from apptools.util import runtools

# new RPC version 2.0
from apptools.rpc import mappers
from apptools.rpc import dispatch

if rule_builders:
    app_rules = reduce(lambda x, y: x + y, [ruleset() for ruleset in rule_builders])
else:
    app_rules = []
sys_config = config.config.get('apptools.system', {})


##### ===== Basic Builtin Handlers ===== #####

## NoOperationHandler
# Throwaway handler that returns `NO-OP` and HTTP 404.
class NoOperationHandler(webapp2.RequestHandler):

    ''' Does nothing. '''

    def noop(self):

        ''' Write NO-OP and 404. '''

        self.response.write('NO-OP')
        self.error(404)

    def get(self, *args, **kwargs):

        ''' Pass to NO-OP handler and 404. '''

        return self.noop()

    def post(self, *args, **kwargs):

        ''' Pass to NO-OP handler and 404. '''

        return self.noop()


## AppAdminHandler
# Entrypoint for the autogenerated admin panel.
class AppAdminHandler(webapp2.RequestHandler):

    ''' Provides a clean admin panel that comes standard with your app. '''

    def get(self):
        self.response.write('Admin panel coming soon.')


## SitemapHandler
# Entrypoint for autogenerated Google Webmaster Tools sitemaps.
class SitemapHandler(webapp2.RequestHandler):

    ''' Automatically generates a sitemap in proper XML format. '''

    def get(self):
        self.response.write('Sitemaps coming soon.')


## CacheManifestHandler
# Entrypoint for autogenerated HTML5 AppCache manifests.
class CacheManifestHandler(webapp2.RequestHandler):

    ''' Automatically generates an HTML5 AppCache manifest in proper format. '''

    def get(self):
        self.response.write('Appcache manifests coming soon')


##### ===== Routing + Route Compilation ===== #####


## Route Mappings
_noop_app = [webapp2.Route('/.*', NoOperationHandler, name='no-op-handler')]
_admin_app = [webapp2.Route('/_app/manage.*', AppAdminHandler, name='admin-handler-root')]
_sitemap_app = [webapp2.Route('/_app/sitemap.*', SitemapHandler, name='sitemap-handler')]
_appcache_app = [webapp2.Route('/_app/manifest.*', CacheManifestHandler, name='cache-manifest-handler')]
if endpoints:
    endpoint = endpoints.api_server([service for name, service in dispatch._resolve_services(load=True)
                                     if hasattr(service, 'api_info')], restricted=False)

## Get builtin apps
_builtin_route_cache = None


def get_builtin_apps():

    ''' Return a list of builtin WSGI applications. This should NOT include _noop_app, which is only present for utility/fallback. '''

    global _builtin_route_cache

    if not _builtin_route_cache:
        _builtin_route_cache = [route for route in reduce(lambda x, y: x + y,
                                                          filter(lambda x: not inspect.isroutine(x), [
                                                          _admin_app,
                                                          _sitemap_app,
                                                          _appcache_app
                                                          ]))]
    return _builtin_route_cache


## @TODO: Export this class to exceptions
class NoURLRules(Exception): pass
if (len(rule_builders) + len(get_builtin_apps())) == 0:
    raise NoURLRules("Could not resolve a URL rule builder.")


##### ===== Runtime Tools/Entrypoints ===== #####

## WSGI/CGI Bridge
def _run(cbk, environ=None, start_response=None):

    ''' Run an app, via CGI or WSGI if possible. '''

    global _noop_app

    ## If no app is passed in, default to no-op...
    if cbk is None:
        cbk = _noop_app

    ## We're running in WSGI...
    if environ is not None and start_response is not None:
        return cbk(environ, start_response)

    ## We're running in CGI...
    else:
        return cbk.run()


## Admin panel run shortcut
def admin(environ=None, start_response=None):

    ''' Run the admin panel app. '''

    global _run
    global _noop_app
    global _admin_app

    try:
        # Make sure we're dealing with an admin...
        from google.appengine.api import users

        if not users.get_current_user() or not users.is_current_user_admin():
            return _run(None, environ, start_response)  # return no-op if they aren't logged in or aren't admin
        else:
            return _run(_admin_app, environ, start_response)  # replace with actual control panel

    except:
        return _run(_noop_app, environ, start_response)  # We're not running on AppEngine


## Sitemap run shortcut
def sitemap(environ=None, start_response=None):

    ''' Run the sitemap generation app. '''

    global _run
    global _sitemap_app

    return _run(_sitemap_app, environ, start_response)


## Appcache run shortcut
def appcache(environ=None, start_response=None):

    ''' Run the appcache manifest generation app. '''

    global _run
    global _appcache_app

    return _run(_appcache_app, environ, start_response)


## Main WSGI dispatch
def gateway(environ=None, start_response=None, direct=False, appclass=webapp2.WSGIApplication):

    ''' Resolve which internal app should be run, then do it. '''

    global _run
    global app_rules
    global sys_config

    ## Get user/app rules, then splice in our internal rules at the end
    routing_rules = [rule for rule in map(lambda x: x() if inspect.isroutine(x) else x,
                                          (app_rules + get_builtin_apps()) + dispatch.mappings())]

    if direct:
        environ['xaf.direct'] = True
        appclass = core.DirectDispatchApplication

    ## Make the WSGI app
    action = _run
    app = core.ApplicationFactory(appclass, routing_rules, debug=config.debug, config=config.config)

    ## Debug Options
    if config.debug:
        runtools.enable_jinja2_debugging()
        if sys_config.get('hooks'):
            if sys_config.get('appstats', False) is True:
                app = runtools.enable_appstats(app)
            if sys_config.get('apptrace', False) is True:
                app = runtools.enable_apptrace(app)
            if sys_config.get('profiler', False) is True:

                # profile_run shim action
                def profile_run(app, environ=None, start_response=None):

                    ''' Wrap our WSGI run action in cProfile. '''

                    import cProfile
                    logging.info('==== PROFILING ENABLED. ====')
                    dump_path = '/'.join(os.path.realpath(__file__).split('/')[0:-1] + ['AppToolsApp.profile'])

                    cProfile.runctx("_run(app, environ, start_response)", globals(), locals(), filename=dump_path)

                action = profile_run
    
    ## Go!
    return action(app, environ, start_response)


## Extension exports
_installed_extensions = {
    'admin': admin,
    'sitemap': sitemap,
    'appcache': appcache
}
