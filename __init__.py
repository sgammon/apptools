# -*- coding: utf-8 -*-

'''

AppTools for Python

ALL RIGHTS RESERVED
Copyright 2012, momentum labs (http://www.momentum.io)
-sam (<sam@momentum.io>)

'''

## Base Imports
import os
import sys
import time
import logging

## Try the app bootstrapper, if it's around
try:
    import bootstrap
    bootstrap.AppBootstrapper.prepareImports()
except:
    # No bootstrapper found.
    pass

## AppTools Util
from apptools.util import debug
from apptools.util import appconfig

wallclock = []

try:
    import config

except ImportError as e:
    cfg = appconfig.ConfigProxy(appconfig._DEFAULT_CONFIG)

else:
    cfg = appconfig.ConfigProxy(config.config)
    config.config = cfg


def clockpoint(name):

    ''' Adds a clockpoint to the wallclock dict above, for easy walltime tracking. '''

    global wallclock
    timepoint = (name, time.time())
    wallclock.append(timepoint)
    return timepoint


## WSGI Gateway
def gateway(environ, start_response):

    ''' Central gateway into AppTools' WSGI dispatch. '''

    from apptools import dispatch

    ## Pass off to dispatch
    return dispatch.gateway(environ, start_response)


## Expose base classes
#_apptools_servicelayer = [messages, fields, middleware, decorators]
#_apptools_base_classes = [BaseHandler, BaseModel, BaseService, BasePipeline, AppException]
#__all__ = [str(i.__class__.__name__) for i in _apptools_base_classes] + _apptools_servicelayer


## For direct/CGI...
if __name__ == '__main__':
    gateway(None, None)
