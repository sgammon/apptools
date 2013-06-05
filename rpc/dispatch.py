# -*- coding: utf-8 -*-

"""
this small service layer subpackage contains utilities
for dispatching and running RPC services.

:author: Sam Gammon (sam@momentum.io)
:copyright: (c) 2013 momentum labs.
:license: This is private source code - Ampush has been granted an
          unlimited, exclusive license for embedded use. For details
          about embedded licenses and other legalese, see `LICENSE.md`.
"""

# 3rd party
import webapp2

# service layer
from apptools import rpc

# App Config
try:
    import config
    _DEBUG = config.debug
except:
    _DEBUG, config = True, False


## Globals
gateway = _application = Application = None


## generate URL mappings
mappings = lambda: rpc._service_mappings(rpc._project_services)


def initialize(services=mappings):

    ''' Initialize the Service Layer. '''

    global gateway, _application, Application, mappings

    ## generate gateway application
    gateway = _application = Application = webapp2.WSGIApplication(mappings, **{
        'debug': _DEBUG,
        'config': config.config if config else {}
    })

    return gateway


if __name__ == '__main__':
    initialize()
