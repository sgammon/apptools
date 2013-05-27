# -*- coding: utf-8 -*-

"""
allows apptools models to be used across
SQL tables, with enhanced mySQL support.

:author: Sam Gammon (sam@momentum.io)
:copyright: (c) 2013 momentum labs.
:license: This is private source code - Ampush has been granted an
          unlimited, exclusive license for embedded use. For details
          about embedded licenses and other legalese, see `LICENSE.md`.
"""

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
