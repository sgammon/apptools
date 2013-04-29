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

except ImportError as e:
    # flag as unavailable
    _PIPELINE, _pipeline_root_class = False, object

else:

    # further imports
    from pipeline import common as _pcommon
    from pipeline import pipeline as _pipeline

    # flag as available
    _PIPELINE, _pipeline_root_class = True, _pipeline.Pipeline

    
    ## PipelineModel
    # Adapt apptools models to appengine pipelines.
    class PipelineModel(ModelAdapter):

        ''' Adapt model classes to Pipelines. '''

        pass


    ## PipelineKey
    # Adapt apptools keys to appengine pipelines.
    class PipelineKey(ModelAdapter):

        ''' Adapt key classes to Pipelines. '''

        pass
