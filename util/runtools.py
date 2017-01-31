# -*- coding: utf-8 -*-

'''

    apptools util: platforms

    small utilities used during WSGI app init/other low level areas of apptools.

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
import logging


def enable_jinja2_debugging():

    ''' Enables blacklisted modules that help Jinja2 debugging. '''

    try:
        # Enables better debugging info for errors in Jinja2 templates.
        from google.appengine.tools.dev_appserver import HardenedModulesHook
        HardenedModulesHook._WHITE_LIST_C_MODULES += ['_ctypes', 'gestalt']
    except:
        pass
    return


def enable_appstats(app):

    ''' Utility function that enables appstats middleware. '''

    try:
        from google.appengine.ext.appstats.recording import appstats_wsgi_middleware
        app.app = appstats_wsgi_middleware(app.app)
    except Exception, e:
        logging.error('Failed to initialize AppStats. Exception encountered: "' + str(e) + '".')
    finally:
        return app


def enable_apptrace(app):

    ''' Utility function that enables apptrace middleware. '''

    try:
        from apptrace import middleware
        middleware.Config.URL_PATTERNS = ['^/$']
        app.app = middleware.apptrace_middleware(app.app)

    except Exception, e:
        logging.error('Failed to initialize AppTrace. Exception encountered: "' + str(e) + '".')

    finally:
        return app
