# -*- coding: utf-8 -*-

'''

    apptools model adapters

	allows apptools models to be adapted to
	just about any backend storage engine!

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


# module constants
__version__ = (0, 5)  # module version-string
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
from . import core
from . import redis
from . import mongo
from . import protorpc
from . import pipeline
from . import memcache
from . import inmemory

modules = (core, sql, redis, mongo, protorpc, pipeline, memcache, inmemory)


# concrete adapters
from .sql import SQLAdapter
from .redis import RedisAdapter
from .mongo import MongoAdapter
from .memcache import MemcacheAdapter
from .inmemory import InMemoryAdapter

concrete = (InMemoryAdapter, RedisAdapter, SQLAdapter, MongoAdapter, MemcacheAdapter)


# builtin mixins
from . import core
from .core import DictMixin
from .core import JSONMixin

builtin_mixins = (DictMixin, JSONMixin)


__adapters__ = abstract_adapters + modules + concrete + builtin_mixins
