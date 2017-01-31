# -*- coding: utf-8 -*-

'''

    apptools rpc: dispatch

    this small service layer subpackage contains utilities
    for dispatching and running RPC services.

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
