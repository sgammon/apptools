# -*- coding: utf-8 -*-

'''

API: Assets

Responsible for reading the assets config (see config/assets.py) and outputting asset
URLs based on the config & resource requested. There is support for switching the
absolute URL base to a CDN hostname, or multiple CDN hostnames. There's also support
for cachebusting via key value pairs, and switching to minified assets.

-sam (<sam@momentum.io>)

'''

## Base Imports
import random
import config as cfg
from config import config
from webapp2 import cached_property

## AppTools Imports
from apptools.api import CoreAPI
from apptools.api import HandlerMixin

## Logging + Exceptions
from apptools.util.debug import AppToolsLogger
from apptools.api.output import CoreOutputAPIException

logging = AppToolsLogger('apptools.core', 'AssetsAPI')

## Global Vars
_img_url_cache = {}
_asset_url_cache = {}


## == Assets Module Exceptions == ##

## AssetException
# Top level exception for all Asset API-related exceptions.
class AssetException(CoreOutputAPIException): ''' Top-level exception for all Asset API-related exceptions. '''

## InvalidAssetType
# Raised when an asset type is invalid.
class InvalidAssetType(AssetException): ''' Raised when a given asset type is not recognized. '''

## InvalidAssetEntry
# Raised when an asset entry is invalid.
class InvalidAssetEntry(AssetException): ''' Raised when a given asset type is valid, but an asset could not be found at the given identifier. '''

## CoreAssetsAPI
# Brokers access and provides generated URLs to registered and unregistered assets.
class CoreAssetsAPI(CoreAPI):

    ''' Responds to requests for image and asset URLs, reads asset configuration & manages caching of asset URLs. '''

    methods = ['script_url', 'style_url', 'asset_url']

    @cached_property
    def _AssetConfig(self):

        ''' Cached access to the Assets config. '''

        return config.get('apptools.project.assets')

    @cached_property
    def _OutputConfig(self):

        ''' Cached access to the Output config. '''

        return config.get('apptools.project.output')

    def _log(self, message, severity='info'):

        ''' Takes in log messages from the API and outputs them according to config. (Errors are always logged) '''

        if severity == 'debug' and self._AssetConfig.get('debug', False) == True:
            if self._AssetConfig.get('verbose', False) == True or cfg.debug == True:
                logging.info('CoreAssets: ' + str(message))
            else:
                logging.debug('CoreAssets: ' + str(message))

        elif severity == 'info' and self._AssetConfig.get('debug', False) == True:
            logging.info('CoreAssets: ' + str(message))

        elif severity == 'error':
            logging.error('CoreAssets: ' + str(message))

        return

    def script_url(self, handler, name, module=None, prefix='static', version=None, minify=False, version_by_getvar=False, **kwargs):

        ''' Return a URL for a script. '''

        return self.asset_url(handler, 'js', name, module, prefix, version, minify, version_by_getvar, **kwargs)

    def style_url(self, handler, name, module=None, prefix='static', version=None, minify=False, version_by_getvar=False, **kwargs):

        ''' Return a URL for a stylesheet. '''

        return self.asset_url(handler, 'style', name, module, prefix, version, minify, version_by_getvar, **kwargs)

    def ext_url(self, handler, name, module=None, prefix='static', version=None, minify=False, version_by_getvar=False, **kwargs):

        ''' Return a URL for a nonregular asset. '''

        return self.asset_url(handler, 'ext', name, module, prefix, version, minify, version_by_getvar, **kwargs)

    def img_url(self, handler, path, name):

        ''' Return a simple URL for an image. (Note: does not use assets config - images are not registered assets) '''

        global _img_url_cache
        identifier = (path, name, handler.force_https_assets, handler.force_absolute_assets, handler.force_hostname)
        if identifier in _img_url_cache:
            return _img_url_cache[identifier]
        else:
            url_fragments = []
            if self._OutputConfig.get('assets', {}).get('serving_mode', 'local') == 'cdn':
                if handler.force_https_assets is True:
                    url_fragments.append('https://')
                else:
                    url_fragments.append('//')
                if hasattr(handler, 'force_hostname') and getattr(handler, 'force_hostname'):
                    cdnprefix = getattr(handler, 'force_hostname')
                elif isinstance(self._OutputConfig['assets']['cdn_prefix'], list):
                    cdnprefix = random.choice(self._OutputConfig['assets']['cdn_prefix'])
                else:
                    cdnprefix = self._OutputConfig['assets']['cdn_prefix']
                url_fragments.append([cdnprefix, 'assets', 'img', 'static'] + [i for i in path.split('/')] + [''])
            else:
                if hasattr(handler, 'force_hostname') and getattr(handler, 'force_hostname'):
                    if hasattr(handler, 'force_https_assets') and getattr(handler, 'force_https_assets') is True:
                        url_fragments.append('https://')
                    else:
                        if handler.request.environ.get('HTTP_SCHEME', 'http').lower() == 'https':
                            url_fragments.append('https://')
                        else:
                            url_fragments.append('http://')
                    url_fragments.append(handler.force_hostname)
                url_fragments.append('/')
                url_fragments.append(['assets', 'img', 'static'] + [i for i in path.split('/')] + [''])

            url_fragments.append(name)

        return reduce(lambda x, y: str(x) + str(y), map(lambda x: isinstance(x, list) and '/'.join(x) or x, url_fragments))

    def asset_url(self, handler, _type, name, module, prefix, version, minify, version_by_getvar, **kwargs):

        ''' Return a URL for an asset, according to the current configuration. '''

        global _asset_url_cache
        identifier = (handler.force_https_assets, handler.force_hostname, handler.force_absolute_assets, _type, name, module, prefix, version, minify, version_by_getvar)
        if identifier in _asset_url_cache:
            return _asset_url_cache[identifier]
        else:

            asset = None
            module_path = None
            module_config = {}

            if _type not in self._AssetConfig:
                raise InvalidAssetType("Asset type '" + str(_type) + "' is invalid for name '" + str(name) + "' in module '" + str(module) + "'.")

            # Grab config and find requested asset
            if _type in self._AssetConfig:
                if name in self._AssetConfig[_type]:
                    asset = self._AssetConfig[_type][name]
                else:
                    for entry in self._AssetConfig[_type]:
                        if isinstance(entry, tuple):
                            if entry[0] == module:

                                if 'config' in self._AssetConfig[_type][(module, entry[1])]:
                                    asset = self._AssetConfig[_type][(module, entry[1])]['assets'].get(name, False)
                                    module_config = self._AssetConfig[_type][(module, entry[1])].get('config', {})
                                else:
                                    asset = self._AssetConfig[_type][(module, entry[1])].get(name, False)

                                if asset is not False:
                                    module_path = entry[1]

                        if asset is False:
                            raise InvalidAssetEntry("Could not resolve asset '" + str(name) + "' under VALID module '" + str(module) + "'.")

            if asset is not None and isinstance(asset, dict):

                # Start building asset URL
                filename = []
                query_string = {}
                asset_url = ['assets', _type, prefix, module_path, ('.', filename)]
                minify = minify or self._OutputConfig['assets'].get('minified', False)

                ## 1: Consider absolute assets
                if 'absolute' in asset:
                    if handler.force_https_assets:
                        abs_url = 'https://'
                    else:
                        abs_url = asset.get('scheme', 'http') + '://'

                    if minify and 'min' in asset and isinstance(asset['min'], basestring):
                        return abs_url + asset.get('min')
                    else:
                        return asset.get('absolute')

                ## 2: Consider relative assets
                else:

                    ## 2.1: Consider path
                    if 'path' in asset:

                        ### Consider version
                        if version is not None or 'version' in asset:
                            if version is None:
                                version = asset['version']

                            version_mode = 'filename'
                            if version_by_getvar is False:
                                if 'version_mode' in asset or 'version_mode' in module_config:
                                    if 'version_mode' in asset:
                                        version_mode = asset['version_mode']
                                    else:
                                        version_mode = module_config['version_mode']
                            else:
                                version_mode = 'getvar'

                            if version_mode == 'filename':
                                filename.append(str(version))
                            elif version_mode == 'getvar':
                                query_string['v'] = str(version)

                        ### Minification in path mode is a path
                        if minify and 'min' in asset and isinstance(asset['min'], basestring):
                            query_string['m'] = '1'
                            pathspec = asset['min'].split('/')
                            filename += pathspec[-1].split('.')

                        ### If there's no minification and we have a path, use it
                        else:
                            pathspec = asset['path'].split('/')
                            filename += pathspec[-1].split('.')

                        asset_url.insert(-1, ('/', pathspec[0:-1]))

                    ## 2.2: Consider no-path
                    else:

                        if 'name' not in asset:
                            filename.append(name)
                        else:
                            filename.append(asset['name'])

                        ### Minification in no-path mode is a boolean (appends .min)
                        if minify and 'min' in asset and isinstance(asset['min'], bool):
                            query_string['m'] = '1'
                            if _type not in frozenset(['style', 'css']):
                                filename.append('min')

                        ### Consider version
                        if version is not None or 'version' in asset:
                            if version is None:
                                version = asset['version']

                            version_mode = 'filename'
                            if version_by_getvar is False:
                                if 'version_mode' in asset or 'version_mode' in module_config:
                                    if 'version_mode' in asset:
                                        version_mode = asset['version_mode']
                                    else:
                                        version_mode = module_config['version_mode']
                            else:
                                version_mode = 'getvar'

                            if version_mode == 'filename':
                                filename.append(str(version))
                            elif version_mode == 'getvar':
                                query_string['v'] = str(version)

                        ### Consider explicit extension
                        if 'extension' in asset:
                            filename.append(asset['extension'])

                        ### Consider implicit extension
                        else:
                            if _type == 'style':
                                filename.append('css')
                            elif _type == 'js':
                                filename.append('js')

                    ## 2.3: Consider arbitrary query string entries
                    if len(kwargs) > 0:
                        for key, value in kwargs.items():
                            query_string[key] = str(value)

                    self._log('Asset URL = ' + str(asset_url), 'info')
                    self._log('Query String = ' + str(query_string), 'debug')

                    ## 2.4: Build relative asset URL
                    if len(query_string) > 0 and self._OutputConfig['assets']['serving_mode'] != 'cdn':
                        compiled_url = reduce(lambda x, y: x + y, ['/', '/'.join(map(lambda x: isinstance(x, tuple) and x[0].join(x[1]) or x, filter(lambda x: x not in [True, False, None], asset_url))), '?', '&'.join([str(k) + '=' + str(v) for k, v in query_string.items()])])
                    else:
                        compiled_url = reduce(lambda x, y: x + y, ['/', '/'.join(map(lambda x: isinstance(x, tuple) and x[0].join(x[1]) or x, filter(lambda x: x not in [True, False, None], asset_url)))])

                    if compiled_url is not None and isinstance(compiled_url, basestring) and len(compiled_url) > 0:

                        if self._OutputConfig['assets']['serving_mode'] == 'local':
                            if cfg.debug is not True:
                                _asset_url_cache[identifier] = compiled_url
                            return compiled_url

                        elif self._OutputConfig['assets']['serving_mode'] == 'cdn':

                            if isinstance(self._OutputConfig['assets']['cdn_prefix'], list):
                                cdnprefix = random.choice(self._OutputConfig['assets']['cdn_prefix'])
                            else:
                                cdnprefix = self._OutputConfig['assets']['cdn_prefix']

                            if cfg.debug is not True:
                                if handler.force_https_assets:
                                    _asset_url_cache[identifier] = ''.join(['https://', cdnprefix] + [compiled_url])
                                else:
                                    _asset_url_cache[identifier] = ''.join(['//', cdnprefix] + [compiled_url])
                                return _asset_url_cache[identifier]
                            else:
                                if handler.force_https_assets:
                                    return ''.join(['https://', cdnprefix] + [compiled_url])
                                else:
                                    return ''.join(['//', cdnprefix] + [compiled_url])
                        return compiled_url

            else:
                if not isinstance(asset, dict):
                    raise InvalidAssetEntry("Could not resolve non-mapping asset by the name of '" + str(name) + "'. Asset value: '" + str(asset) + "'.")

                if module not in self._AssetConfig[_type] and name not in self._AssetConfig[_type]:
                    raise InvalidAssetEntry("Could not resolve asset '" + str(name) + "' in module '" + str(module) + "'.")

_api = CoreAssetsAPI()


## AssetsMixin
# Used as an addon class to BaseHandler, etc. to add util methods to retrieve assets.
class AssetsMixin(HandlerMixin):

    ''' Bridge the Core Assets API to methods on a handler. '''

    _assets_api = _api
    _gathered_assets = []
    _gathered_asset_lookup = {}

    def _record_linked_asset(self, type, ref, priority=None):

        ''' Record a dependent asset for the requested resource in the _gathered_assets list. '''

        if type is not None and ref is not None:
            if ref in self._gathered_asset_lookup.get('seen', set([])):
                return ref
            else:
                asset_id = (type, ref, priority)
                self._gathered_assets.append(asset_id)
                if self._gathered_asset_lookup.get('seen') is None:
                    self._gathered_asset_lookup['seen'] = set([])
                self._gathered_asset_lookup['seen'].add(ref)
                self._gathered_asset_lookup[ref] = self._gathered_assets.index(asset_id)
        return ref

    def get_img_asset(self, *args, **kwargs):

        ''' Proxy in the current handler. '''

        return self._record_linked_asset('image', self._assets_api.img_url(self, *args, **kwargs))

    def get_style_asset(self, *args, **kwargs):

        ''' Proxy in the current handler. '''

        return self._record_linked_asset('style', self._assets_api.style_url(self, *args, **kwargs))

    def get_script_asset(self, *args, **kwargs):

        ''' Proxy in the current handler. '''

        return self._record_linked_asset('script', self._assets_api.script_url(self, *args, **kwargs))

    def get_asset(self, *args, **kwargs):

        ''' Proxy in the current handler. '''

        return self._record_linked_asset('unknown', self._assets_api.asset_url(self, *args, **kwargs))
