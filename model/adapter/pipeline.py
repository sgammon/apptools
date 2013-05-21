# -*- coding: utf-8 -*-

"""
--------------------------------------
apptools2: model adapter for pipelines
--------------------------------------

allows apptools models to be seamlessly
passed back-and-forth between pipelines.

:author: Sam Gammon (sam@momentum.io)
:copyright: (c) 2013 momentum labs.
:license: This is private source code - Ampush has been granted an
          unlimited, exclusive license for embedded use. For details
          about embedded licenses and other legalese, see `LICENSE.md`.
"""

# adapter API
from .abstract import ModelAdapter


# try to find appengine pipelines
try:
    # force absolute import to prevent infinite recursion
    pipeline = __import__('pipeline', tuple(), tuple(), [], -1)

except ImportError as e:
    # flag as unavailable
    _PIPELINE, _pipeline_root_class = False, object

else:  # pragma: no cover
    # extended imports
    _pcommon = getattr(__import__('pipeline', tuple(), tuple(), ['common'], -1), 'common')
    _pipeline = getattr(__import__('pipeline', tuple(), tuple(), ['pipeline'], -1), 'pipeline')
    
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
