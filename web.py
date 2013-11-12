# -*- coding: utf-8 -*-

'''

    apptools web

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

# app / 3rd party
try:
    import config; _APPCONFIG = True
except:
    config, _APPCONFIG = {}, False

import webapp2

# apptools
from . import core

# apptools util
from .util import decorators


@decorators.config(debug=True, path='api.classes.WebHandler')
class WebHandler(core.BaseHandler):

    ''' Root web handler. '''

    # Preloader / Sessions
    preload = None  # holds preloaded template, if supported
    template = None  # string path to associated template

    # Config Paths
    _jinja2_config_path = 'webapp2_extras.jinja2'
    _p_output_config_path = 'apptools.project.output'

    # RPC Transport Settings
    transport = {

        'secure': config.production,  # whether to communicate over HTTPS (switches on production deployment)
        'consumer': 'apptools-sample' if (config.production is True) else 'apptools-sample-sandbox',  # API consumer name
        'endpoint': 'api.fatcatmap.com' if (config.production is True) else '127.0.0.1:8080',  # API endpoint

        'realtime': {  # realtime / websocket settings
            'enabled': False,  # enable/disable realtime
            'endpoint': None,  # endpoint for realtime sockets
            'secure': False  # whether to communicate over HTTPS
        }

    }

    ## ++ Internal Shortcuts ++ ##
    @decorators.memoize
    @decorators.classproperty
    def _outputConfig(cls):

        ''' Cached access to base output config.

            :returns: Configuration ``dict`` for the :py:mod:`apptools`
                      *Core Output API*, which provides integration with
                      :py:mod:`jinja2`, among other things. '''

        return config.config.get(cls._p_output_config_path, {'debug': True})  # pragma: no cover

    @decorators.memoize
    @decorators.classproperty
    def _jinjaConfig(cls):  # pragma: no cover

        ''' Cached access to base output config.

            :returns: Configuration ``dict`` for the :py:mod:`apptools`
                      *Core Output API*, which provides integration with
                      :py:mod:`jinja2`, among other things. '''

        return config.config.get(cls._jinja2_config_path)  # pragma: no cover

    ## Internals
    @decorators.memoize
    def hostname(self):

        ''' Return proxied or request hostname. In cases where :py:mod:`apptools`
            is running on specialized infrastructure, :py:mod:`appfactory` provides
            the ability to override the current hostname via the ``XAF-Hostname``
            header.

            :returns: Active hostname (``str``). Either parses from the
                      current :py:class:`webapp2.Request` (which uses
                      uses the ``Host:`` header), or returns an overridden
                      hostname from :py:mod:`appfactory`. '''

        return self.request.host if not self.force_hostname else self.force_hostname

    @decorators.memoize
    def baseTransport(self):

        ''' Return a clean set of transport base settings.

            :returns: Base configuration ``dict`` for page transports, like
                      JSONRPC and WebSockets. '''

        return {
            'secure': False,
            'endpoint': self.hostname,
            'consumer': 'apptools-sandbox',
            'scope': 'readonly',
            'realtime': {'enabled': False},
            'make_object': lambda x: self._make_services_object(x)
        }

    @decorators.memoize
    def computedTransport(self):

        ''' Overlay this handler's transport settings on the app's base settings and return.

            :returns: Computed + collapsed configuration ``dict`` for page
                      transports, like JSONRPC and WebSockets. '''

        b = dict(((k, v) for k, v in self.baseTransport.items()))
        b.update(self.transport)
        return b

    @decorators.memoize
    def template_environment(self):

        ''' Return a new environment, because if we're already here it's not cached.

            :returns: New or existing :py:class:`jinja2.environment.Environment`. '''

        return self.jinja2

    @decorators.memoize
    def jinja2(self):

        ''' Cached access to Jinja2.

            :returns: New or existing :py:class:`jinja2.environment.Environment`. '''

        ## Patch in dynamic content support
        return self._output_api.get_jinja(self.app, self.dynamicEnvironmentFactory) if hasattr(self, 'dynamicEnvironmentFactory') else self._output_api.get_jinja(self.app, self.jinja2EnvironmentFactory)

    def _preload_data(self):

        ''' Preloaded data support.

            :returns: Current ``WebHandler`` (``self``) for method chainability. '''

        self.logging.info('Data preloading currently disabled.')
        return self

    def _preload_template(self):

        ''' Preloaded template support.

            :returns: Current ``WebHandler`` (``self``) for method chainability. '''

        if hasattr(self, 'template') and getattr(self, 'template') not in frozenset(['', None, False]):
            self.preload_template(self.template)
        return self

    def _make_services_object(self, services):

        ''' Make a dict suitable for JSON representing an API service.

            :param services: Dictionary service configuration to generate
                             service description object from.

            :returns: Materialized configuration array, suitable for
                      serilization and inlining into the page. '''

        return [[
            service,
            cfg['methods'],
            opts
        ] for service, action, cfg, opts in services['services_manifest']]

    def _bindRuntimeTemplateContext(self, context):

        ''' Bind a bunch of utils-n-stuff at runtime.

            :param context: Current :py:mod:`jinja2` template context ``dict``.

            :returns: Updated context ``dict``. This method **must** return the
                      appropriately-mutated context, or it will be dropped. '''

        context.update({

            '_meta': config.config.get('apptools.output.meta'),
            '_opengraph': config.config.get('apptools.output.meta', {}).get('opengraph', {}),
            'handler': self,
            'transport': {
                'services': self.computedTransport,
                'realtime': {
                    'enabled': False
                }
            },
            'security': {
                'current_user': None
            }

        })

        return super(WebHandler, self)._bindRuntimeTemplateContext(context)

    ## ++ External Methods ++ ##
    def initialize(self, request, response):

        ''' Initialize this handler.

            :param request: Current or empty :py:class:`webapp2.Request`.
            :param response: Current or empty :py:class:`webapp2.Response`.

            :returns: Currently-active ``WebHandler`` descendent, for method
                      chainability. '''

        super(core.BaseHandler, self).initialize(request, response)
        return self

    def dispatch(self):

        ''' Dispatch a response for a given request using this handler.

            :returns: Attribute :py:attr:`WebHandler.response`, which is
                      the resulting response from a dispatched HTTP-based
                      method, such as ``WebHandler.GET``. '''

        try:
            from __main__ import bootstrapper
            bootstrapper.preload(config.debug)
        except ImportError:
            pass  # no bootstrapper, no problem

        try:
            _super = super(WebHandler, self)
            response = _super.dispatch()

            if isinstance(response, basestring):
                self.response.write(response)

            elif isinstance(response, webapp2.Response):
                self.response = response

            elif response is None:
                response = self.response

        except Exception, e:

            if config.debug:
                raise
            else:
                self.handle_exception(e)

        return self.response

    ## Render APIs
    def render(self, *args, **kwargs):

        ''' If supported, pass off to dynamic render, which rolls-in support for editable content blocks.

            :param args: Positional arguments to :py:meth:`jinja2.render_template`.
            :param kwargs: Keyword arguments to overlay onto the active template context.
            :returns: Rendered content, via :py:mod:`jinja2`. '''

        if hasattr(self, 'content'):
            return self.content.render(*args, **kwargs)
        return super(WebHandler, self).render(*args, **kwargs)

    ## HTTP Methods
    def head(self):

        ''' Run GET, if defined, and return the headers only (method for ``HTTP HEAD``).

            :returns: Stringified response from ``GET`` call, with response body removed. '''

        response = None
        if hasattr(self, 'get'):
            response = self.get()
            response.body = ''
        if response is None:
            self.response.write('')
        return self.response

    def options(self):

        ''' Run GET, clear response, return headers only (method for ``HTTP OPTIONS``).

            :returns: Stringified list of supported HTTP methods, including headers like ``HEAD``,
                      with ``GET`` response body removed. '''

        for k, v in self.baseHeaders.iteritems():
            if k.lower() == 'access-control-allow-origin':
                if v is None:
                    self.response.headers[k] = self.request.headers['origin']
            else:
                self.response.headers[k] = v
        return self.response.write(','.join((i for i in frozenset(['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
                                             if hasattr(self, i.lower()))))
