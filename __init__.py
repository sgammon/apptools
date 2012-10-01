# -*- coding: utf-8 -*-

'''

AppTools for Python

ALL RIGHTS RESERVED
Copyright 2012, momentum labs (http://www.momentum.io)
-sam (<sam@momentum.io>)

'''

## Base Imports
import time
import config
import logging

## Try the app bootstrapper, if it's around
try:
    import bootstrap
    bootstrap.AppBootstrapper.prepareImports()
except:
    logging.warning('Could not resolve app bootstrapper.')
    if config.debug:
        raise
    else:
        pass

## Base Classes
from apptools.core import BaseHandler
from apptools.model import BaseModel
from apptools.services import BaseService
from apptools.exceptions import AppException

try:
	from apptools.pipelines import BasePipeline

except ImportError:
	BasePipeline = type('BasePipeline', (object,), {})

## Service Layer Exports
from apptools.services import fields
from apptools.services import messages
from apptools.services import middleware
from apptools.services import decorators


wallclock = []


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
_apptools_servicelayer = [messages, fields, middleware, decorators]
_apptools_base_classes = [BaseHandler, BaseModel, BaseService, BasePipeline, AppException]
__all__ = [str(i.__class__.__name__) for i in _apptools_base_classes] + _apptools_servicelayer


## For direct/CGI...
if __name__ == '__main__':
    gateway(None, None)
