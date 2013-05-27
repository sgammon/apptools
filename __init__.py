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
    pass  # pragma: no cover

## AppTools Util
from apptools.util import appconfig

try:
    import config

except ImportError as e:  # pragma: no cover
    cfg = appconfig.ConfigProxy(appconfig._DEFAULT_CONFIG)

else:
    cfg = appconfig.ConfigProxy(config.config)
    config.config = cfg


## WSGI Gateway
def gateway(environ, start_response):

    ''' Central gateway into AppTools' WSGI dispatch. '''

    from apptools import dispatch  # pragma: no cover
    return dispatch.gateway(environ, start_response)  # pragma: no cover


## Expose base classes
#_apptools_servicelayer = [messages, fields, middleware, decorators]
#_apptools_base_classes = [BaseHandler, BaseModel, BaseService, BasePipeline, AppException]
#__all__ = [str(i.__class__.__name__) for i in _apptools_base_classes] + _apptools_servicelayer


## For direct/CGI...
if __name__ == '__main__':
    gateway(None, None)  # pragma: no cover
