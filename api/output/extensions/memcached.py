# -*- coding: utf-8 -*-
import webapp2
from config import config
from google.appengine.api import memcache

from jinja2 import MemcachedBytecodeCache as BytecodeCache


## MemcachedBytecodeCache - caches and loads compiled template bytecode with memcache
class MemcachedBytecodeCache(BytecodeCache):

    ''' Extends Jinja2 to use memcache for template bytecode. '''

    __configPath = 'apptools.output.extension.MemcachedBytecodeCache'

    @webapp2.cached_property
    def __extensionConfig(self):

        ''' Cached shortcut to full extension config. '''

        return config.get(self.__configPath)

    @webapp2.cached_property
    def __innerConfig(self):

        ''' Cached shortcut to this extension's config block. '''

        return self.__extensionConfig.get('config')

    def __init__(self):

        ''' Init super, but properly instantiate for AppEngine. '''

        super(MemcachedBytecodeCache, self).__init__(
            memcache.Client(),
            prefix=self.__innerConfig.get('prefix'),
            timeout=self.__innerConfig.get('timeout'))
