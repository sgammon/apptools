# -*- coding: utf-8 -*-

# Pipeline Imports
import logging

try:
    import pipeline

    ## BasePipeline
    # This base class provides pipeline utilities.
    class BasePipeline(pipeline.Pipeline):
        pass

except ImportError:
    logging.critical('GAE lib "Pipelines" is not installed.')
else:

    ## BasePipeline
    # This is injected just in case pipelines is not installed.
    class BasePipeline(object):
        pass
