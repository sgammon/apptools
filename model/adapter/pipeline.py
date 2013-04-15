# -*- coding: utf-8 -*-

'''

    apptools2: model adapter for pipelines
    -------------------------------------------------
    |                                               |   
    |   `apptools.model.adapter.pipelines`          |
    |                                               |
    |   allows apptools models to be seamlessly     |
    |   passed back-and-forth between pipelines.    |
    |                                               |   
    -------------------------------------------------
    |   authors:                                    |
    |       -- sam gammon (sam@momentum.io)         |
    -------------------------------------------------   
    |   changelog:                                  |
    |       -- apr 1, 2013: initial draft           |
    -------------------------------------------------

'''

# adapter API
from .abstract import ModelAdapter


# try to find appengine pipelines
try:
    import pipeline
    from pipeline import common as _pcommon
    from pipeline import pipeline as _pipeline

except ImportError as e:
    # flag as unavailable
    _PIPELINE, _pipeline_root_class = False, object

else:
    # flag as available
    _PIPELINE, _pipeline_root_class = True, _pipeline.Pipeline


## PipelineAdapter
# Adapt apptools models to appengine pipelines.
class PipelineAdapter(ModelAdapter):

    ''' Adapt model classes to Pipelines. '''

    @classmethod
    def is_supported(cls):

        ''' Check whether this adapter is supported in the current environment. '''

        return False
