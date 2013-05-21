# -*- coding: utf-8 -*-

"""
----------------------------------
apptools2: model adapter for mongo
----------------------------------

allows apptools models to be stored and
retrieved using mongoDB.

:author: Sam Gammon (sam@momentum.io)
:copyright: (c) 2013 momentum labs.
:license: This is private source code - Ampush has been granted an
          unlimited, exclusive license for embedded use. For details
          about embedded licenses and other legalese, see `LICENSE.md`.
"""

# adapter API
from .abstract import ModelAdapter


## MongoAdapter
# Adapt apptools models to MongoDB.
class MongoAdapter(ModelAdapter):

    ''' Adapt model classes to MongoDB. '''

    @classmethod
    def is_supported(cls):

        ''' Check whether this adapter is supported in the current environment. '''

        return False
