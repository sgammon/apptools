# -*- coding: utf-8 -*-

'''

    apptools2: model adapter for SQL
    -------------------------------------------------
    |                                               |   
    |   `apptools.model.adapter.sql`                |
    |                                               |
    |   allows apptools models to be used across    |
    |   SQL tables, with enhanced mySQL support.    |
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


## SQLAdapter
# Adapt apptools models to SQL-like engines.
class SQLAdapter(ModelAdapter):

    ''' Adapt model classes to SQL. '''

    @classmethod
    def is_supported(cls):

        ''' Check whether this adapter is supported in the current environment. '''

        return False
