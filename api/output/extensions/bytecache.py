# -*- coding: utf-8 -*-
import webapp2
from config import config
from jinja2 import MemcachedBytecodeCache as BytecodeCache

## Global Cache
_template_bytecode = {}


## ThreadedBytecodeCache - caches and loads compiled template bytecode with thread memory
class ThreadedBytecodeCache(BytecodeCache):

    ''' Extends Jinja2 to use thread memory for template bytecode. '''

    __configPath = 'apptools.output.extension.ThreadedBytecodeCache'

    @webapp2.cached_property
    def __extensionConfig(self):

        ''' Cached shortcut to full extension config. '''

        return config.get(self.__configPath)

    @webapp2.cached_property
    def __innerConfig(self):

        ''' Cached shortcut to this extension's config block. '''

        return self.__outputConfig.get('config')

    def __init__(self, directory):

        ''' Init super, but properly instantiate for AppEngine. '''

        super(ThreadedBytecodeCache, self).__init__(self, prefix=self.__innerConfig.get('prefix'), timeout=self.__innerConfig.get('timeout'))

    def get(self, key):

        ''' Get bytecode from threadcache at a key. '''

        pass

    def set(self, key, value, timeout):

        ''' Set bytecode into threadcache at a given key. '''

        pass
