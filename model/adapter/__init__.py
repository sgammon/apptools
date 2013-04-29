# -*- coding: utf-8 -*-

'''

    apptools2: model adapters
    -------------------------------------------------
    |                                               |
    |   `apptools.model.adapter`                    |
    |                                               |
    |   allows apptools models to be adapted to     |
    |   just about any backend storage engine!      |
    |                                               |
    -------------------------------------------------
    |   authors:                                    |
    |       -- sam gammon (sam@momentum.io)         |
    -------------------------------------------------
    |   changelog:                                  |
    |       -- apr 1, 2013: initial draft           |
    -------------------------------------------------

'''

# module constants
__version__ = (0, 2)  # module version-string
__doc__ = "Contains modules that adapt apptools models to various storage backends."


# abstract adapters
from . import abstract
from .abstract import Mixin
from .abstract import KeyMixin
from .abstract import ModelMixin
from .abstract import ModelAdapter
from .abstract import IndexedModelAdapter

abstract_adapters = (abstract, ModelAdapter, IndexedModelAdapter)


# adapter modules
from . import sql
from . import redis
from . import mongo
from . import protorpc
from . import pipeline
from . import memcache
from . import inmemory

modules = (sql, redis, mongo, protorpc, pipeline, memcache, inmemory)


# concrete adapters
from .sql import SQLAdapter
from .redis import RedisAdapter
from .mongo import MongoAdapter
from .protorpc import ProtoRPCAdapter
from .pipeline import PipelineAdapter
from .memcache import MemcacheAdapter
from .inmemory import InMemoryAdapter

concrete = (InMemoryAdapter, RedisAdapter, SQLAdapter, MongoAdapter, ProtoRPCAdapter, PipelineAdapter, MemcacheAdapter)

__all__ = abstract_adapters + modules + concrete
