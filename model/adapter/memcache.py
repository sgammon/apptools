# -*- coding: utf-8 -*-

'''

    apptools2: model adapter for memcache
    -------------------------------------------------
    |                                               |
    |   `apptools.model.adapter.memcache`           |
    |                                               |
    |   allows apptools models to be stored and     |
    |   retrieved using memcache.                   |
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


## MemcacheAdapter
# Adapt apptools models to Memcache.
class MemcacheAdapter(ModelAdapter):

    ''' Adapt model classes to Memcache. '''

    @classmethod
    def is_supported(cls):

        ''' Check whether this adapter is supported in the current environment. '''

        return False
