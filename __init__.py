# -*- coding: utf-8 -*-

'''

AppTools for Python

ALL RIGHTS RESERVED
Copyright 2012, momentum labs (http://www.momentum.io)
-sam (<sam@momentum.io>)

'''

## Base Imports
import time

## Base Classes
from apptools.core import BaseHandler
from apptools.model import BaseModel
from apptools.services import BaseService
from apptools.pipelines import BasePipeline
from apptools.exceptions import AppException

## Service Layer Exports
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
    pass


## Expose base classes
_apptools_base_classes = [BaseHandler, BaseModel, BaseService, BasePipeline, AppException]
__all__ = [str(i.__class__.__name__) for i in _apptools_base_classes]
