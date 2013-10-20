# -*- coding: utf-8 -*-

'''

    apptools model adapter: pipelines

    allows apptools models to be seamlessly
    passed back-and-forth between pipelines.

    :author: Sam Gammon <sam@momentum.io>
    :copyright: (c) momentum labs, 2013
    :license: The inspection, use, distribution, modification or implementation
              of this source code is governed by a private license - all rights
              are reserved by the Authors (collectively, "momentum labs, ltd")
              and held under relevant California and US Federal Copyright laws.
              For full details, see ``LICENSE.md`` at the root of this project.
              Continued inspection of this source code demands agreement with
              the included license and explicitly means acceptance to these terms.

'''


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
