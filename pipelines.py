# -*- coding: utf-8 -*-

'''

AppTools Pipelines

Holds BasePipeline to be exported by core, and includes any code or features
built around AppEngine Pipelines.

-sam (<sam@momentum.io>)

'''

# Pipeline Imports
import config
import webapp2

from apptools.util import debug
from apptools.util import platform
from apptools.util import datastructures

logging = debug.AppToolsLogger('apptools.pipelines')


try:
    import pipeline

    ## BasePipeline
    # This base class provides pipeline utilities.
    @platform.PlatformInjector
    class BasePipeline(pipeline.Pipeline, datastructures.StateManager):

        # Pipeline State
        state = {}

        # Template Context
        context = {}
        context_injectors = []

        @webapp2.cached_property
        def logging(self):

            ''' Named log pipe. '''

            global logging
            return logging.extend(name=self.__class__.__name__)

        @webapp2.cached_property
        def _pipelineConfig(self):

            ''' Cached shortcut to pipelines configuration. '''

            return config.config.get('apptools.pipelines')


except ImportError:
    logging.critical('GAE lib "Pipelines" is not installed.')
else:

    ## BasePipeline
    # This is injected just in case pipelines is not installed.
    @platform.PlatformInjector
    class BasePipeline(object):
        pass
