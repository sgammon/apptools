# -*- coding: utf-8 -*-

'''

    apptools output extensions: memcache

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

# apptools
from apptools.util import debug


## Globals
logger = debug.AppToolsLogger(path='apptools.api.output.extensions', name='memcached')


try:
    from google.appengine.api import memcache
except ImportError as e:
    try:
        import memcache
    except ImportError as e:
        try:
            import umemcache as memcache
        except ImportError as e:
            logger.critical('No memcache adapter found!')
            pass
    _APPENGINE = False
else:
    _APPENGINE = True


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
