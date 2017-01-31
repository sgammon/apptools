# -*- coding: utf-8 -*-

'''

    apptools output extensions: bytecache

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


# 3rd party
import webapp2
from config import config
from jinja2 import MemcachedBytecodeCache as BytecodeCache


## Globals
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
