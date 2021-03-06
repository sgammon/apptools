# -*- coding: utf-8 -*-

'''

    apptools core

    this is the heart and soul of AppTools. Modules, plugins, etc are pulled in here
    into a contiguous structure that resembles a framework. Also hosts BaseHandler.

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


# Base Imports
import os
import webapp2

# Appconfig
try:
    import config; _APPCONFIG = True
except:
    config, _APPCONFIG = None, False

# AppFactory Integration
try:
    import appfactory
except:
    appfactory = False

# Datastructures
from apptools.util import debug
from apptools.util import platform
from apptools.util import datastructures

## WebOb
# AppTools uses some stuff directly from WebOb. For example, many AppTools exceptions inherit from WebOb objects.
from webob import exc

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

            # Pre-dispatch hook
            callchain = filter(lambda x: hasattr(x, 'pre_dispatch'), self.platforms[:])
            if len(callchain) > 0:
                for platform in callchain:
                    try:
                        platform.pre_dispatch(self)

                    except exc.HTTPFound as e:
                        self.logging.info('Redirect encountered in pre_dispatch.')

                        # Force-put session ticket and data
                        self.session.commit()
                        return self.response

                    except Exception, e:
                        self.logging.error('Encountered unhandled exception "%s" in platform pre_dispatch hook for installed platform "%s".' % (e, platform))
                        if (not _APPCONFIG) or config.debug:
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

        if not self.direct:
            # Check platforms for post-dispatch hooks
            if (hasattr(self, 'platforms') and isinstance(self.platforms, list)) and len(self.platforms) > 0:
                callchain = filter(lambda x: hasattr(x, 'post_dispatch'), reversed(self.platforms[:]))
                if len(callchain) > 0:
                    for platform in callchain:
                        try:
                            result = platform.post_dispatch(self, result)
                        except Exception, e:
                            self.logging.error('Encountered unhandled exception "%s" in platform post_dispatch hook for installed platform "%s".' % (e, platform))
                            if (not _APPCONFIG) or config.debug:
                                raise
                            else:
                                continue

        if self.direct:
            return self
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
            'analytics': {} if not _APPCONFIG else config.config.get('apptools.project.output', {}).get('analytics', {}),  # analytics settings
            'channel': {
                'enabled': self.push.session,  # enable/disable appengine channel API
                'token': self.push.token  # token for connecting channel
            },
            'request': self.request,  # the active request
            'route': self.request.route,  # the route that was matched
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


## ApplicationFactory
# Dynamically produces a WSGI application class, suitable for direct-dispatch.
class ApplicationFactory(object):

    ''' Factory for generating WSGI application objects. '''

    def __new__(self, target=webapp2.WSGIApplication, *args, **kwargs):

        ''' Factory a new WSGI application object. '''

        return target(*args, **kwargs)


## DirectDispatchApplication
# Modified WSGI application class that returns a response object directly, rather than the app iterator.
class DirectDispatchApplication(webapp2.WSGIApplication):

    ''' Allows an application to be directly-dispatched, such that a WebOb response is returned rather than a content generator. '''

    def __call__(self, environ, start_response):

        ''' Dispatched upon receiving a request. '''

        # Default to indirect dispatch
        if 'xaf.direct' in environ and environ.get('xaf.direct', False) is True:
            self.direct = True
        else:
            self.direct = False

        with self.request_context_class(self, environ) as (request, response):
            try:
                if request.method not in self.allowed_methods:
                    # 501 Not Implemented
                    raise exc.HTTPNotImplemented()

                rv = self.router.dispatch(request, response)
                if rv is not None:
                    response = rv

            except Exception as e:
                try:
                    rv = self.handle_exception(request, response, e)
                    if rv is not None:
                        response = rv

                except exc.HTTPException, e:
                    # Use the HTTP exception as response.
                    response = e

                except Exception, e:
                    response = self._internal_error(e)

            try:
                if self.direct:
                    return response
                else:
                    return response(environ, start_response)

            except Exception as e:
                return self._internal_error(e)(environ, start_response)
