# -*- coding: utf-8 -*-

'''

AppTools Core

This is the heart and soul of AppTools. Modules, plugins, etc are pulled in here
into a contiguous structure that resembles a framework. Also hosts BaseHandler.

-sam (<sam@momentum.io>)

'''

# Base Imports
import os
import config
import webapp2

# AppFactory Integration
try:
    import appfactory
except:
    appfactory = False

# Datastructures
from apptools.util import debug
from apptools.util import platform
from apptools.util import datastructures

## Webapp2
# AppTools uses [Webapp2](webapp-improved.appspot.com) for WSGI internals, session handling, request dispatching, etc.
from webapp2 import Response
from webapp2 import RequestHandler

## AppTools APIs
# Internal APIs for gluing all the pieces together.
from apptools.api import BaseObject

## Assets API
# AppTools includes an [asset management API](api/assets.html) for easily outputting links to static or dynamic images, js, stylesheets, or other site assets.
from apptools.api.assets import AssetsMixin

## Output API
# AppTools includes an [integrated output API](api/output.html) for easily loading and executing Jinja2 templates.
# The output loader **automatically defaults to compiled templates** when running in production.
from apptools.api.output import OutputMixin

## Services API
# AppTools includes a full [service layer](services/index.html) for building Python/JSON-backed AJAX API services.
from apptools.api.services import ServicesMixin

## Push API
# AppTools includes full integration with the [App Engine Channel API](https://developers.google.com/appengine/docs/python/channel/) for performing server-side push to HTTP clients.
from apptools.api.push import PushMixin

## Logging Controller
# This will soon replace PY's builtin logging system.
logging = debug.AppToolsLogger('apptools.core')


## AbstractPlatformHandler
# Injects abstract root platform mixins, where appripriate.
if appfactory and isinstance(appfactory, type(os)):

    from appfactory import integration

    ## Root Abstract Platform - AppFactory
    class AbstractPlatformHandler(BaseObject, RequestHandler, integration.AppFactoryMixin):

        ''' Injects AppFactory configuration, shortcut, and state properties. '''

        _appfactory_enabled = True

else:

    ## Vanilla Root Abstract Platform
    class AbstractPlatformHandler(BaseObject, RequestHandler):

        ''' Used as a base platform handler when no platform integration is enabled. '''

        _appfactory_enabled = False


## BaseHandler
# Base request handler class, with shortcuts, utilities, and base template context.
@platform.PlatformInjector
class BaseHandler(AbstractPlatformHandler, AssetsMixin, ServicesMixin, OutputMixin, PushMixin):

    ''' Top-level parent class for request handlers in AppTools. '''

    # Class Properties
    uagent = {}
    direct = False
    context = {}
    platforms = []

    # Internal stuff
    response = Response
    configPath = 'apptools.project'
    context_injectors = []

    # Base HTTP Headers
    @webapp2.cached_property
    def logging(self):

        ''' Named log pipe. '''

        global logging
        return logging.extend('RequestHandler', self.__class__.__name__)

    ## Dispatch
    def dispatch(self):

        ''' Sniff the Uagent header, then pass off to Webapp2. '''

        # Collect super dispatch
        s_dispatch = super(BaseHandler, self).dispatch

        # Consider direct dispatch
        if self.request.environ.get('xaf.direct'):
            self.direct = True
        else:
            self.direct = False

        # Check platforms for pre-dispatch hooks
        if (hasattr(self, 'platforms') and isinstance(self.platforms, list)) and len(self.platforms) > 0:
            callchain = filter(lambda x: hasattr(x, 'pre_dispatch'), self.platforms[:])
            if len(callchain) > 0:
                for platform in callchain:
                    try:
                        platform.pre_dispatch(self)
                    except Exception, e:
                        self.logging.error('Encountered unhandled exception "%s" in platform pre_dispatch hook for installed platform "%s".' % (e, platform))
                        if config.debug:
                            raise
                        else:
                            continue
        # Sniff Uagent
        if self.request.headers.get('User-Agent', None) is not None and len(self.uagent) == 0:
            try:
                # Pass through httpagentparser
                self.uagent = self.util.httpagentparser(self.request.headers.get('User-Agent'))
                self.uagent['original'] = self.request.headers.get('User-Agent')
            except Exception, e:
                self.logging.warning('Exception encountered parsing uagent: ' + str(e))
                pass

        # Dispatch method (GET/POST/etc.)
        result = super(BaseHandler, self).dispatch()

        # Check platforms for post-dispatch hooks
        if (hasattr(self, 'platforms') and isinstance(self.platforms, list)) and len(self.platforms) > 0:
            callchain = filter(lambda x: hasattr(x, 'post_dispatch'), self.platforms[:])
            if len(callchain) > 0:
                for platform in callchain:
                    try:
                        result = platform.post_dispatch(self, result)
                    except Exception, e:
                        self.logging.error('Encountered unhandled exception "%s" in platform post_dispatch hook for installed platform "%s".' % (e, platform))
                        if config.debug:
                            raise
                        else:
                            continue

        if self.direct and not isinstance(result, webapp2.Response):
            return self.response
        return result

    ## Exceptions
    def handle_exception(self, exception, debug):

        ''' Handle an unhandled exception during method dispatch. '''

        self.logging.exception('Unhandled exception encountered in RequestHandler code: "%s".' % exception)
        if debug:
            raise
        else:
            self.error(500)

    ## Bind runtime template context variables (overridden in sub handlers to allow injection into the template context)
    def _bindRuntimeTemplateContext(self, context):

        ''' Bind variables to the template context related to the current request context. '''

        ## Create the page context
        context['page'] = {

            'ie': False,  # are we serving to IE?
            'mobile': False,  # are we serving to mobile?
            'tablet': False,  # are we serving to a tablet?
            'analytics': config.config.get('apptools.project.output', {}).get('analytics', {}),  # analytics settings
            'channel': {
                'enabled': self.push.session,  # enable/disable appengine channel API
                'token': self.push.token  # token for connecting channel
            },
            'appcache': {
                'enabled': False,  # enable/disable appcaching
                'location': None  # location for appcache manifest
            },
            'services': {
                'services_manifest': self.make_services_manifest(),  # services manifest
                'global_config': self._globalServicesConfig  # global services config
            },  # enable API services

        }

        ## Consider Uagent stuff
        if self.uagent is not None and len(self.uagent) > 0:

            # Detect if we're handling a request from IE, and if we are, tell the template context
            if 'MSIE' in self.uagent.get('browser', {}).get('name', ''):
                self.logging.info('Uagent detected as Microsoft Internet Explorer.')
                context['page']['ie'] = True
                context['page']['legacy'] = True

            # Detect Android clients
            elif 'Android' in self.uagent.get('browser', {}).get('name', ''):
                self.logging.info('Uagent detected as Android.')
                context['page']['mobile'] = True
                context['page']['android'] = True

            # Detect iPhone clients
            elif 'iPhone' in self.uagent.get('browser', {}).get('name', ''):
                self.logging.info('Uagent detected as iPhone.')
                context['page']['mobile'] = True
                context['page']['ios'] = True

            # Detect iPad clients
            elif 'iPad' in self.uagent.get('browser', {}).get('name', ''):
                self.logging.info('Uagent detected as iPad.')
                context['page']['mobile'] = True
                context['page']['tablet'] = True
                context['page']['ios'] = True

            # Mobile and legacy clients are not bleeding-edge
            if not context['page'].get('mobile', False) and not context['page'].get('legacy', False):

                try:
                    vsplit = self.uagent.get('browser', {}).get('version', '').split('.')

                    # Chrome detection
                    if self.uagent.get('browser', {}).get('name', '').lower() == 'chrome':

                        if int(vsplit[0]) >= 15:
                            ## Chrome 15 or better gets bleeding-edge status
                            context['page']['robust'] = True

                        else:
                            context['page']['robust'] = False

                    # Safari detection
                    elif self.uagent.get('browser', {}).get('name', '').lower() == 'safari':

                        if int(vsplit[0]) >= 5:
                            ## Safari 5 or better gets bleeding-edge status
                            context['page']['robust'] = True

                        else:
                            context['page']['robust'] = False

                    # Firefox detection
                    elif self.uagent.get('browser', {}).get('name', '').lower() == 'firefox':

                        if int(vsplit[0]) >= 15:
                            ## Firefox 15 or better gets bleeding-edge status
                            context['page']['robust'] = True

                        else:
                            context['page']['robust'] = False

                    # Opera detection
                    elif self.uagent.get('browser', {}).get('name', '').lower() == 'opera':

                        if int(vsplit[0]) >= 9:
                            ## Opera 9 or better gets bleeding-edge status
                            context['page']['robust'] = True

                        else:
                            context['page']['robust'] = False

                except:
                    context['page']['robust'] = False
            else:
                context['page']['robust'] = False

            context['page']['agent'] = self.uagent

        return context
