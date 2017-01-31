#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''

    apptools util: development server

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
import re
import sys
import glob
import gzip
import time
import hashlib
import inspect
import datetime

# apptools
from apptools.util import debug

# = App Config = #
try:
    import config as appconfig
except ImportError:
    class Config(object):
        debug = True
        config = {}
    appconfig = Config()

# = Server Runtime = #
try:
  from gevent import pool
  from gevent import wsgi
  from gevent import monkey

except ImportError:

  ENGINE = "wsgiref"

  ## stdlib wsgi server
  from wsgiref.simple_server import make_server

  def server(interface, port, *args, **kwargs):

    ''' Shim to run with a stdlib WSGI server. '''

    return make_server(interface, port, *args, **kwargs)

else:

  ENGINE = "gevent"

  ## monkey patch stdlib
  monkey.patch_all()

  ## gevent will be our server today
  def server(interface, port, *args, **kwargs):

    ''' Shim to run with a gevent-based PyWSGI server. '''

    return wsgi.WSGIServer((interface, port), *args, spawn=pool.Pool(1000), **kwargs)


## Globals
static_cache = {}
HTTP_DATE_FMT = "%a, %d %b %Y %H:%M:%S %Z"  # date format for HTTP headers
config = appconfig.config.get('devserver', {'debug': True, 'bind': {'port': 8080}})
logging = debug.AppToolsLogger(path='apptools.util', name='devserver')._setcondition(config.get('debug', appconfig.debug))


def devhandler(app=None, static=True, logging=None, path=None):

  ''' Closure to wrap an app callable into the ``locals`` context for
      :py:func:`handle`, which presents a WSGI-compliant interface for
      dispatching requests in an apptools development environment.

      :param app: Application that should be dispatched if the requested
      path doesn't match static ones.

      :param static: Whether to respond to typical apptools static asset
      routes - i.e. CSS and JS. Defaults to ``True``. Passing ``False``
      will cause the ``handle`` function to pass the request on to
      ``apptools`` no matter what, which is useful sometimes (for instance,
      a WSGI server for apptools services only).

      :param logging: Override the standard logger for the local devserver,
      for instance to redirect logging to a file. Passing ``None`` (the
      default) will use a module-global logger from
      :py:mod:`apptools.util.devserver`.

      :param path: Path prefix (usually absolute) to prepend to file paths
      for the purpose of resolving & serving static files. Defaults to
      ``None`` which won't prepend anything.

      :returns: Prepared WSGI-compliant development handler, named handle. '''

  def handle(environ, start_response):

    ''' WSGI-compliant handler to replace standard static routing and
        proper reverse-proxying in a development environment. You should
        never use this in production, that would be a *terrible* idea.

        :py:func:`devserver` wraps this to create and bind a simple dev
        server. This function acts as the WSGI gateway and handles basic
        static asset serving, headers and response procedures.

        :param environ: Environment dictionary, as provided according
        to the WSGI specification.

        :param start_response: Callback function to begin the response
        process with a status line and headers. '''

    ## globals
    global static_cache

    ## dispatch entrypoints
    from apptools import dispatch
    from apptools.rpc import mappers
    from apptools.rpc import dispatch as rpc

    appconfig.debug = True  # we are running locally, it's always dev time

    ## Environment stuff
    environ['SERVER_SOFTWARE'] = "apptools/%s/dev" % ENGINE
    environ['SERVER_ENVIRONMENT'] = "Development/1.0"

    if not static or (not environ.get('PATH_INFO', '/').startswith('/assets')):

      # it's an app path, defer to apptools
      response = (app or dispatch.gateway)(environ, start_response)
      return response

    else:

      # setup response headers and default response status
      status, headers = '200 OK', []

      # it's a static asset path
      try:
        filepath = os.path.abspath(  # make absolute...
          os.path.join(              # a joined path...
            path or '', '/'.join(filter(lambda x: x != '', (  # of the current file's directory, plus...
              # ... the path to the static file we want, potentially splitting out the query string ...
              environ['PATH_INFO'].split('?')[0] if '?' in environ['PATH_INFO'] else environ['PATH_INFO']
            ).split('/')))))

        # check the static cache if it's enabled
        if config.get('static', {}).get('caching', {}).get('enabled', False) and (filepath in static_cache):

          mtime, mimetype, contents, chash = static_cache[filepath]

          # expires
          headers.append(('Expires', (
            datetime.datetime.now() + datetime.timedelta(seconds=config.get('static', {}).get('caching', {}).get('timeout', 30))
              ).strftime(HTTP_DATE_FMT)
          ))

          # etag
          headers.append(('Etag', chash[len(chash) - 8:]))

          # cache-control
          headers.append(('Cache-Control', '%s; max-age=%s' % (
            config.get('static', {}).get('caching', {}).get('mode', 'private'),
            config.get('static', {}).get('caching', {}).get('timeout', 30)
          )))

          headers.append(('Content-Type', mimetype))

          # has file been modified on-disk?
          if not int(os.path.getmtime(filepath)) > mtime:

            if environ and config.get('static', {}).get('caching', {}).get('serve304', False):

              if 'HTTP_IF_NONE_MATCH' in environ:
                # check hash against theirs
                if chash[len(chash) - 8:] == environ['HTTP_IF_NONE_MATCH']:
                  # we can 304 :)
                  status = '304 Not Modified'
                  start_response(status, headers)
                  return iter([''])  # 304 responses don't have a body

              elif 'HTTP_IF_MODIFIED_SINCE' in environ:

                # check their copy
                if_modified_date = int(time.mktime(datetime.datetime.strftime(environ['HTTP_IF_MODIFIED_SINCE'], HTTP_DATE_FMT).timetuple()))

                if if_modified_date >= mtime:
                  # cached and we can 304 :)
                  status = '304 Not Modified'
                  start_response(status, headers)
                  return iter([''])  # 304 responses don't have a body

                else:
                  pass  # must re-send (static cache is up to date, browser's isn't)

              else:
                # cached but can't 304
                start_response(status, headers)
                return iter([contents])

          else:
            # it has been modified, invalidate cache
            del static_cache[filepath]

        # not cached / caching is off
        with open(filepath, 'r') as asset_handle:
          mtime, contents = int(os.path.getmtime(filepath)), asset_handle.read()

          # resolve mimetype
          mimetype = {

            # mapped content types
            'css': 'text/css',
            'js': 'application/javascript',
            'svg': 'image/svg+xml',
            'png': 'image/png',
            'gif': 'image/gif',
            'jpeg': 'image/jpeg',
            'jpg': 'image/jpg',
            'webp': 'image/webp',
            'manifest': 'text/cache-manifest',
            'txt': 'text/plain',
            'html': 'text/html',
            'xml': 'text/xml',
            'json': 'application/json'

          }.get(filepath.split('.')[-1], 'application/octet-stream')

        # set in local cache
        if config.get('static', {}).get('caching', {}).get('enabled', False):
          static_cache[filepath] = mtime, mimetype, contents, hashlib.sha256(contents).hexdigest() if contents else None

        start_response(status, headers)
        return iter([contents])

      except IOError as e:
        
        import pprint;

        if 'no such file' in str(e).lower():
          ## 404 time nao
          status, message = '404', 'Not Found'

        elif 'permission denied' in str(e).lower():
          ## 403 time you scoundrel
          status, message = '403', 'Forbidden'

        start_response('%s %s' % (status, message), [('Content-Type', 'text/plain')])

        return iter(['''

          <!doctype html>
          <html>
            <head>
              <title>%s</title>
            </head>
            <body>
              <h2>%s</h2>
              <br /><br />
              <b>Context:</b>
              <pre>
                 %s
              </pre>
              <br />
              <br />
              <b>Exception:</b>
              <pre>
                 %s
              </pre>
            </body>
          </html>

        ''' % (status, message, pprint.pprint(environ), pprint.pprint(e))])
  
  return handle


def devserver(root=None, interface='127.0.0.1', port=8080, label=None, services_only=False, dispatcher=None, logger=None, cli=True, construct_only=False):

  ''' Run a development server powering the locally-installed
      ``apptools`` application. Uses ``wsgiref`` or ``gevent``,
      depending on what's available. Once a server is constructed,
      it can either be returned or ``serve_forever`` will be
      called for the user, depending on the ``construct_only``
      *kwarg*.

      :param root: Document root for the devserver. Relative asset
      paths will be resolved against this path prefix.

      :param interface: Internet Protocol (IP) address to bind the
      devserver to. Defaults to ``127.0.0.1``.

      :param port: Port to bind the devserver to. Defaults to the
      standard HTTP alt of ``8080``.

      :param label: Something in human-friendly text to identify
      the app that we'll be running. Defaults to ``app``.

      :param services_only: Boolean flag indicating that we should
      only serve services, and not match static asset routes.
      Defaults to ``False``.

      :param dispatcher: Dispatcher callable that we should use in
      the devhandler, if ``services_only`` is truthy or a static
      asset route could not be matched. Defaults to ``apptools``'
      standard gateway - :py:func:`apptools.dispatch.gateway`.

      :param logger: Logger override to force devserver logging to
      occur through a specific object. Defaults to the module-global
      logger for :py:mod:`apptools.util.devserver`.

      :param cli: Boolean flag indicating that we're running under
      a command line. This will take Python exceptions and convert
      them to Unix-style return codes instead of re-raising. Defaults
      to ``True``.

      :param construct_only: Boolean flag indicating that we should
      only construct the local devserver, not bind and ``serve_forever``.
      Returns the constructed server and handler instead.

      :raises Exception: Re-raises exceptions encountered during
      WSGI processing flow, unless ``cli`` is truthy, in which
      case a Unix-style return code is provided.

      :returns: Unix-style return code if ``cli`` is truthy. Otherwise,
      returns ``True`` on success. Re-raises exceptions. '''

  # here's what we're gonna do
  logging.debug('Using WSGI engine `%s`.' % ENGINE)
  logging.info('Serving %s on %s:%s...' % (label, interface, port))

  # we need to convert to unix return codes....
  try:
    if not dispatcher:
      if not services_only:
        dispatcher, label = devhandler(None, logging=logger or logging, path=root or os.getcwd()), label or 'app'  # ``None`` as dispatcher will default to apptools ``dispatch.gateway``
      else:
        dispatcher, label = devhandler(rpc.initialize(), static=False, logging=logger or logging, path=root or os.getcwd()), label or 'services'

    # construct server and bind
    httpd = server(interface, port, dispatcher)

    # optionally only construct the server
    if construct_only: return httpd

    # serve forever, yo
    httpd.serve_forever()
    return 0 if cli else True

  except Exception as e:
    if not cli:
      raise
    print "Encountered exception: %s" % e
    return 1
