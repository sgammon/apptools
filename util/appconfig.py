# -*- coding: utf-8 -*-

'''

Util: Config

Holds utilities for dealing with application config, and the default config set.

-sam (<sam@momentum.io>)

'''

# Base Imports
import copy
import webapp2
import hashlib

# Constants
_DEFAULT_CONFIG = {

    'webapp2': {
        'sup': False
    },

    'webapp2_extras.jinja2': {
        'template_path': 'templates/source',
        'compiled_path': 'templates.compiled',
        'force_compiled': False,
        'environment_args': {
            'optimized': True,
            'autoescape': True,
            'trim_blocks': False,
            'auto_reload': True,
            'extensions': ['jinja2.ext.autoescape', 'jinja2.ext.with_', 'jinja2.ext.loopcontrols']
        }
    },

    'apptools': {

    },

    'apptools.system': {

        'config': {
            'debug': False
        }

    },

    'apptools.model': {

        'default': 'ndb',  # default storage engine

        'engines': [
            {'name': 'NDB', 'enabled': False, 'path': 'apptools.model.adapter.ndb.NDB'},
            {'name': 'Redis', 'enabled': False, 'path': 'apptools.model.adapter.redis.Redis'},
            {'name': 'Memcache', 'enabled': False, 'path': 'apptools.model.adapter.memcache.Memcache'}
        ]

    },

    'apptools.system.platform': {

        'installed_platforms': [
            {'name': 'Generic WSGI', 'path': 'apptools.platform.generic.GenericWSGI'},
            {'name': 'Layer9/AppFactory', 'path': 'apptools.platform.appfactory.AppFactory'},
            {'name': 'Google AppEngine', 'path': 'apptools.platform.appengine.GoogleAppEngine'}
        ]

    },

    'apptools.services': {
        'logging': True,
        'hooks': {
            'appstats': {'enabled': False},
            'apptrace': {'enabled': False},
            'profiler': {'enabled': False}
        },

        'mappers': [

            # Feed-Format Mappers
            {'name': 'RSS', 'enabled': False, 'path': 'apptools.services.mappers.RSSRPCMapper'},
            {'name': 'ATOM', 'enabled': False, 'path': 'apptools.services.mappers.ATOMRPCMapper'},

            # RPC Protocol Format Mappers
            {'name': 'XMLRPC', 'enabled': False, 'path': 'apptools.services.mappers.XMLRPCMapper'},
            {'name': 'JSONRPC', 'enabled': True, 'path': 'apptools.services.mappers.JSONRPCMapper'},

            # Encoded Protocol Format Mappers
            {'name': 'Protobuf', 'enabled': False, 'path': 'apptools.services.mappers.ProtobufRPCMapper'},
            {'name': 'URLEncoded', 'enabled': False, 'path': 'apptools.services.mappers.URLEncodedRPCMapper'}

        ],

        'middleware': [

            ('authentication', {

                ## Configuration for authentication middleware
                'enabled': True,
                'debug': True,
                'path': 'apptools.services.middleware.AuthenticationMiddleware',
                'args': {
                }
            }),

            ('monitoring', {

                ## Configuration for monitoring middleware
                'enabled': True,
                'debug': True,
                'path': 'apptools.services.middleware.MonitoringMiddleware',
                'args': {
                }
            }),

            ('authorization', {

                ## Configuration for authorization middleware
                'enabled': True,
                'debug': True,
                'path': 'apptools.services.middleware.AuthorizationMiddleware',
                'args': {
                }
            }),

            ('caching', {

                ## Configuration for caching middleware
                'enabled': True,
                'debug': True,
                'path': 'apptools.services.middleware.CachingMiddleware',
                'args': {
                }
            })

        ],

        'middleware_config': {

            'caching': {
                'profiles': {
                    'none': {
                        'localize': False,
                        'default_ttl': None,
                        'activate': {
                            'local': False,
                            'request': False,
                            'internal': False
                        }
                    },
                    'lazy': {},
                    'safe': {},
                    'aggressive': {},
                },

                'default_profile': 'none'

            },

            'security': {
                'profiles': {
                    'none': {
                        'expose': 'all',
                        'authentication': {
                            'enabled': False
                        },
                        'authorization': {
                            'enabled': False
                        }
                    },
                    'public': {
                        'expose': 'all',
                        'authentication': {
                            'enabled': False,
                            'mode': None
                        },
                        'authorization': {
                            'enabled': False,
                            'mode': None
                        }
                    },
                    'private': {
                        'expose': 'admin',
                        'authentication': {
                            'enabled': False,
                            'mode': None
                        },
                        'authorization': {
                            'enabled': False,
                            'mode': None
                        }
                    }
                },

                'default_profile': 'none'
            }
        },

        'defaults': {
            'module': {},
            'service': {

                'config': {
                    'caching': 'none',
                    'security': 'none',
                    'recording': 'none'
                },
                'args': {}

            }
        }
    },

    'apptools.project': {

        'name': 'AppTools',
        'version': {
            'major': 0,
            'minor': 0,
            'micro': 1,
            'build': 20111111,
            'release': 'ALPHA'
        }

    },

    'apptools.project.services': {

        'debug': False,
        'enabled': True,
        'logging': False,

        'config': {
            'hmac_hash': hashlib.sha512,
            'url_prefix': '/_api/rpc',
            'secret_key': 'VNDIvnbB80gh@!H!)@*HJBXCVPOIUCNbi9j0-9u)!U(@)!N'
        },

        'services': {

            ## System API - for testing/dev
            'system': {
                'enabled': True,
                'service': 'apptools.services.builtin.SystemService',
                'methods': ['echo', 'hello', 'whoareyou', 'manifest'],

                'config': {
                        'caching': 'none',
                        'security': 'none',
                        'recording': 'none'
                }
            }

        }

    },

    'apptools.project.output': {
        # Output Configuration
        'minify': False,      # whether to minify page output or not
        'optimize': True,     # whether to use the async script loader or not
        'standalone': False,  # whether to render only the current template, or the whole context (ignores "extends")

        'analytics': {  # Analytics Settings
            'enable': True,              # whether to insert analytics code
            'multitrack': True,          # whether to enable support for multiple trackers
            'anonymize': False,          # whether to anonymize IPs before analytics
            'account_id': {
                'dev': 'UA-25133943-6',         # used when running from the devserver
                'staging': 'UA-25133943-6',    # used on the staging version of the site
                'production': 'UA-25133943-6'  # used on the production version of the site
            },
            'sitespeed': {
                'enable': True,           # enable google analytics' site speed tracking
                'sample': 100            # set the sitespeed sample rate
            },
            'webclient':{
                'dev': 'https://ssl.google-analytics.com/u/ga_debug.js',
                'http': 'https://deliver.lyr9.net/analytics/ga.js',
                'https': 'https://deliver.lyr9.net/analytics/ga.js'
            }
        },

        'appcache': {  # HTML5 appcaching
            'enable': False,                       # whether to enable
            'manifest': 'scaffolding-v1.appcache'  # manifest to link to
        },

        'assets': {  # Asset API
            'minified': False,        # whether to switch to minified assets or not
            'serving_mode': 'local',  # 'local' or 'cdn' (CDN prefixes all assets with an absolute URL)
            'cdn_prefix': ['deliver.lyr9.net']  # CDN prefix/prefixes - a string is used globally, a list of hostnames is selected from randomly for each asset
        },

        'headers': {  # Default Headers (only supported headers are shown)
            'Cache-Control': 'private,max-age=3600',  # default to not caching dynamic content
            'X-UA-Compatible': 'IE=edge,chrome=1',  # http://code.google.com/chrome/chromeframe/
            'XAF-Origin': 'GAE_FCM_SANDBOX',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'XAF-Session, XAF-Token, XAF-Channel, XAF-Socket, X-ServiceClient, Content-Type, X-ServiceTransport',
            'Access-Control-Expose-Headers': 'XAF-Session, XAF-Token, XAF-Channel, XAF-Socket, X-Platform, Content-Type'
        }
    },

    'apptools.project.output.template_loader': {

        'force': True,
        'debug': False,
        'use_memcache': False,
        'use_memory_cache': False

    },

    'layer9.appfactory': {

    }

}


## ConfigProxy
# Wraps app configuration, enabling log messages on config access/write.
class ConfigProxy(object):

    ''' Wraps app configuration to enable debug features. '''

    _i = 0
    _oc = None
    debug = False
    _config = None
    _lookup = None

    def __init__(self, config):

        ''' Initialize this object. '''

        self._config, self._oc, self._lookup = copy.deepcopy(config), config.items(), set(config.keys())

    @webapp2.cached_property
    def logging(self):

        ''' Named logging pipe. '''

        from apptools.util import debug
        self.debug = self._config.get('apptools.system', {}).get('config', {}).get('debug', False)
        return debug.AppToolsLogger(path='app', name='Config')._setcondition(self.debug)

    def __iter__(self):

        ''' Return raw config for iteration. '''

        self._i = 0  # reset iteration index
        return self

    def next(self):

        ''' Return the next item in this iteration. '''

        # proxy iteration to our encapsulated config dictionary
        if self._i == len(self._oc) - 1:
            self._i = 0
            raise StopIteration
        else:
            self._i = self._i + 1
            return self._oc[self._i]

    def __getitem__(self, item):

        ''' Return an item in config. '''

        # redirect config access to dictionary
        self.logging.info("Config access: '%s'." % item)
        if item in self._lookup:
            return self._config[item]
        else:
            raise KeyError("No config entry by the name '%s'." % item)

    def __setitem__(self, item, value):

        ''' Set an item in config. '''

        if item not in self._lookup:
            self._lookup.add(item)
        self.logging.info("Config write: '%s'=>'%s'." % (item, value))
        self._config[item] = value
        self._oc.append((item, value))
        return value

    def __contains__(self, item):

        ''' Contains redirect. '''

        return item in self._lookup

    def _overlay(self, mapping, rov=None):

        ''' Recursively update config, from target `mapping`. '''

        if not isinstance(mapping, dict):
            return mapping
        if rov is None:
            rov = dict(self._config.items()[:])
        for k, v in mapping.iteritems():
            if k in rov and isinstance(rov[k], dict):
                rov[k] = self._overlay(v, rov[k])
            else:
                rov[k] = v
        return rov

    def overlay(self, mapping):

        ''' Exported method for recursively updating config. '''

        return ConfigProxy(self._overlay(mapping))

    def get(self, name, default=None):

        ''' Retrieve an item from config without raising an AttributeError. '''

        self.logging.info("Config access: '%s'." % name)
        return self._config.get(name, default)

    def items(self):

        ''' Retrieve a set of (key, value) tuples. '''

        return [i for i in self._oc]

    def iteritems(self):

        ''' Generate a set of (key, value) tuples. '''

        for i in self._oc:
            yield i
