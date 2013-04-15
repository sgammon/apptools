# -*- coding: utf-8 -*-

'''

    apptools2: model adapter for mongo
    -------------------------------------------------
    |                                               |   
    |   `apptools.model.adapter.mongo`              |
    |                                               |
    |   allows apptools models to be stored and     |
    |   retrieved using mongoDB.                    |
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


## MongoAdapter
# Adapt apptools models to MongoDB.
class MongoAdapter(ModelAdapter):

    ''' Adapt model classes to MongoDB. '''

    @classmethod
    def is_supported(cls):

        ''' Check whether this adapter is supported in the current environment. '''

        return False
