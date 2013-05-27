# -*- coding: utf-8 -*-

"""
allows apptools models to be stored and
retrieved using memcache.

:author: Sam Gammon (sam@momentum.io)
:copyright: (c) 2013 momentum labs.
:license: This is private source code - Ampush has been granted an
          unlimited, exclusive license for embedded use. For details
          about embedded licenses and other legalese, see `LICENSE.md`.
"""

# adapter API
from .abstract import ModelAdapter


## MemcacheAdapter
# Adapt apptools models to Memcache.
class MemcacheAdapter(ModelAdapter):

    ''' Adapt model classes to Memcache. '''

    @classmethod
    def is_supported(cls):

        ''' Check whether this adapter is supported in the current environment. '''

        return False
