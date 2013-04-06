# -*- coding: utf-8 -*-
import webapp2
from config import config
from apptools.util import debug
from jinja2 import MemcachedBytecodeCache as BytecodeCache

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
