# -*- coding: utf-8 -*-

'''

AppTools Pipelines

Holds BasePipeline to be exported by core, and includes any code or features
built around AppEngine Pipelines.

-sam (<sam@momentum.io>)

'''

# Pipeline Imports
import logging
from apptools.util import platform

try:
    import pipeline

    ## BasePipeline
    # This base class provides pipeline utilities.
    @platform.PlatformInjector
    class BasePipeline(pipeline.Pipeline):
        pass

except ImportError:
    logging.critical('GAE lib "Pipelines" is not installed.')
else:

    ## BasePipeline
    # This is injected just in case pipelines is not installed.
    @platform.PlatformInjector
    class BasePipeline(object):
        pass
