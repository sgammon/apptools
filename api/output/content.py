# -*- coding: utf-8 -*-

'''

    apptools output API: dynamic content

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


## == Imports == ##

## Base Imports
import time
import json
import config
import webapp2
import hashlib

## Jinja2 Imports
from jinja2 import nodes
from jinja2 import Template
from jinja2 import environment
from jinja2.ext import Extension
from jinja2.bccache import BytecodeCache
from jinja2.exceptions import TemplateNotFound

## Core Imports
from apptools.api import CoreAPI

## AppTools Imports
from apptools.api import output
from apptools.util import debug
from apptools.util import AppToolsJSONEncoder

## External Imports
from apptools.util import timesince
from apptools.util import byteconvert

try:
    ## NDB Imports
    from google.appengine.ext import ndb
    from google.appengine.ext.ndb import context
    from google.appengine.ext.ndb import tasklet as ntasklet
    from google.appengine.ext.ndb import synctasklet as stasklet

    ## SDK Imports
    from google.appengine.api import memcache
    from google.appengine.ext import blobstore

except ImportError as e:
    _APPENGINE = False  # we're not running on appengine

    def tasklet(func):

        ''' Shim for missing tasklets. '''

        return func

    toplevel = tasklet  # shim toplevel too

else:
    _APPENGINE = True  # we are running on appengine
    tasklet = mtasklet  # patch in tasklets
    toplevel = ndb.toplevel  # patch in toplevel


## Builtin models
from apptools import model
from apptools.model import builtin as models


## == Globals == ##

## Cached Objects
_output_loader = None
_output_extensions = {}
_output_bytecacher = None

## Global Defaults
_SYSTEM_NAMESPACE = "__system__"
_blocktypes = frozenset(['area', 'snippet', 'summary'])
_dynamic_inheritance_nodes = (nodes.Extends, nodes.FromImport, nodes.Import, nodes.Include)

## Global Query Options
if _APPENGINE:
    _keys_only_opt = ndb.QueryOptions(keys_only=True, limit=3, read_policy=ndb.EVENTUAL_CONSISTENCY, produce_cursors=False, hint=ndb.QueryOptions.ANCESTOR_FIRST, deadline=3)
    _projection_opt = ndb.QueryOptions(keys_only=False, limit=3, read_policy=ndb.EVENTUAL_CONSISTENCY, produce_cursors=False, hint=ndb.QueryOptions.ANCESTOR_FIRST, deadline=3)


## CoreContentAPI - manages the retrieval and update of dynamically editable site content
class CoreContentAPI(CoreAPI):

    ''' Core API for fulfilling, rendering and managing dynamic content-related requests. '''


    ## == API State == ##

    # Content Models
    seen = set([])   # seen keys
    areas = {}       # content areas
    futures = {}     # data futures
    snippets = {}    # content snippets
    summaries = {}   # content summaries
    namespaces = {}  # content namespaces

    # Structure Cache
    templates = {}   # templates cache
    keygroups = {}   # keygroups active
    heuristics = {}  # keygroup heuristics


    ## == Low-level Methods == ##
    def _filter_key(self, k):

        ''' Filter a key in a batch key list. '''

        if _APPENGINE:
            if isinstance(k, basestring):
                try:
                    k = ndb.Key(urlsafe=k)
                except:
                    raise
            elif isinstance(k, ndb.Model):
                k = k.key
        else:
            if isinstance(k, basestring):
                try:
                    k = model.Key.from_urlsafe(k)
                except:
                    raise
            elif isinstance(k, model.Model):
                k = k.key
        return k

    def _filter_model(self, m):

        ''' Filter a model in a batch model list. '''

        if _APPENGINE:
            if not isinstance(m, ndb.Model):
                return False
        else:
            if not isinstance(m, model.Model):
                return False
        return True

    def _fulfill(self, key):

        ''' Fulfill a model, given a key, either from local cache or the datastore. '''

        key = self._filter_key(key)
        if key in self.seen:
            cached_model = {
                models.ContentNamespace: self.namespaces,
                models.ContentArea: self.areas,
                models.ContentSnippet: self.snippets,
                models.ContentSummary: self.summaries
            }.get(key.kind()).get(key)

            # perhaps it's already here?
            if cached_model is not None:

                # yay
                return cached_model

            # perhaps we're still waiting?
            elif key in futures:

                # block :(
                return self.futures.get(key).get_result()

            else:
                # wtf why was it seen then
                return key.get()
        else:
            # just get it
            return key.get()

    @tasklet
    def _batch_fulfill(self, batch, query=None, **kwargs):

        ''' Synchronously retrieve a batch of keys. '''

        # if it's a future, we're probably coming from a now-finished query
        if isinstance(batch, ndb.Future):
            batch = batch.get_result()

        # if it's not a list make it a list (obvs cuz this is _batch_ fulfill)
        if not isinstance(batch, list):
            batch = [batch]

        # filter out so we only get keys
        keys = map(self._filter_key, batch)

        # check for the hashed keygroup
        keygroup_s = tuple([s for s in keys])
        heuristic = self.heuristics.get(keygroup_s)
        if heuristic is not None:
            return [m for b, m in self.keygroups.get(heuristic)]

        return ndb.get_multi(keys, **kwargs)

    @tasklet
    def _batch_fulfill_async(self, batch, query=None, resultset_callback=None, item_callback=None, **kwargs):

        ''' Asynchronously retrieve a batch of keys. '''

        # if it's a future, we're probably coming from a now-finished query
        if isinstance(batch, ndb.Future):
            batch = batch.get_result()

        # if it's not a list make it a list (obvs cuz this is _batch_ fulfill async)
        if not isinstance(batch, list):
            batch = [batch]

        # build fetch!
        keys = map(self._filter_key, batch)

        # check for the hashed keygroup
        keygroup_s = tuple([s for s in keys])
        heuristic = self.heuristics.get(keygroup_s)
        if heuristic is not None:
            if resultset_callback:
                resultset_callback([m for b, m in self.keygroups.get(heuristic)], query=query)
            elif item_callback:
                map(lambda x: item_callback(x, query=query), [m for b, m in self.keygroups.get(heuristic)])
        else:

            # build operations
            op = ndb.get_multi_async(batch, **kwargs)

            # if we want results in batch
            if resultset_callback and not item_callback:

                # build a dependent multifuture that waits on all to finish
                multifuture = ndb.MultiFuture()

                # add each operation as a dependent
                for f in op:
                    multifuture.add_dependent(f)

                # close dependents
                multifuture.complete()

                # add callback to catch results in batch
                if query:
                    multifuture.add_callback(resultset_callback, multifuture, query=query)
                else:
                    multifuture.add_callback(resultset_callback, multifuture)

            # if we want results one by one
            elif item_callback and not resultset_callback:

                # add the item callback to each future
                for f in op:
                    f.add_callback(item_callback, f, query=query)

            # parallel yield!
            yield tuple(op)

    @tasklet
    def _run_query(self, query, count=False, **kwargs):

        ''' Synchronously run a query. '''

        # if we should count first, count
        if not isinstance(count, int) and count == True:
            count = query.count()

        # pull via count or via kwargs
        if isinstance(count, int):
            return query.fetch(count, **kwargs)
        return query.fetch(**kwargs)

    @tasklet
    def _run_query_async(self, query, count=False, future=None, resultset_callback=None, item_callback=None, eventual_callback=None, **kwargs):

        ''' Asynchronously run a query. '''

        # if we just counted
        if future:

            # we have a limit
            count = future.get_result()

            # there are no results
            if count == 0:
                yield resultset_callback([], query=query)

        # if we should count first, kick off a count and call self with the result
        if not isinstance(count, int) and count is True:
            future = query.count_async(**kwargs)
            future.add_callback(self._run_query_async, query, False, future, resultset_callback, item_callback, **kwargs)
            yield future

        else:

            # if we want to go over things in batch
            if resultset_callback and not item_callback:
                if isinstance(count, int):
                    future = query.fetch_async(count, **kwargs)
                else:
                    future = query.fetch_async(**kwargs)
                if eventual_callback:
                    future.add_callback(resultset_callback, future, query=query, resultset_callback=eventual_callback)
                else:
                    future.add_callback(resultset_callback, future, query=query)

            # if we want to go over things one at a time
            elif item_callback and not resultset_callback:
                if isinstance(count, int):
                    future = query.map_async(item_callback, limit=count, **kwargs)
                else:
                    future = query.map_async(item_callback, **kwargs)

            yield future

    @tasklet
    def _batch_store_callback(self, result, query=None):

        ''' Callback for asynchronously retrieved results. '''

        # landing from a query
        if isinstance(result, ndb.Future):
            result = result.get_result()

        # should really be a list
        if not isinstance(result, list):
            result = [result]

        _batch = []
        timestamp = int(time.time())
        for i in filter(self._filter_model, result):

            if i.key not in self.seen:
                self.seen.append(i.key)
            _batch.append((i.key, i))

            if isinstance(i, models.ContentNamespace):
                self.namespaces.get(i.key, {}).update({'model': i, 'timestamp': timestamp})

            elif isinstance(i, models.ContentArea):
                self.areas.get(i.key, {}).update({'model': i, 'timestamp': timestamp})

            elif isinstance(i, models.ContentSnippet):
                self.snippets.get(i.key, {}).update({'model': i, 'timestamp': timestamp})

            elif isinstance(i, models.ContentSummary):
                self.summaries.get(i.key, {}).update({'model': i, 'timestamp': timestamp})

        # generate the keygroup's signature and use it to look for an existing heuristics hint
        keygroup_s = tuple([b for b, i in _batch])
        keygroup_i = self.heuristics.get(keygroup_s, False)

        # trim the old one
        if keygroup_i:
            self.keygroups.remove(keygroup_i)

        # add the new keygroup and map it
        self.keygroups.append(_batch)
        self.heuristics[keygroup_s] = self.keygroups.index(_batch)

    def _build_keysonly_query(self, kind, parent=None, **kwargs):

        ''' Build a keys-only ndb.Query object with the _keys_only options object. '''

        return kind.query(ancestor=parent, default_options=_keys_only_opt.merge(ndb.QueryOptions(**kwargs)))

    def _build_projection_query(self, kind, properties, parent=None, **kwargs):

        ''' Build a projection ndb.Query object with the default _projection_opt options object. '''

        return kind.query(ancestor=parent, default_options=_projection_opt.merge(ndb.QueryOptions(projection=properties, **kwargs)))

    def _build_keygroup(self, keyname, namespace, snippet=False, summary=False):

        ''' Build a group of keys, always containing a ContentNamespace and ContentArea, optionally with a Snippet and Summary. '''

        keygroup = []

        # calculate namespace key
        namespace_key = self._build_namespace_key(namespace)
        keygroup.append(namespace)

        # calculate area key
        area_key = self._build_area_key(keyname, namespace)
        keygroup.append(area_key)

        # if a snippet key is requested
        if snippet:

            # you can pass a version into snippet manually, or True
            if isinstance(snippet, int):
                snippet_key = self._build_snippet_key(keyname, namespace, area_key, snippet)
            else:
                snippet_key = self._build_snippet_key(keyname, namespace, area_key)
            keygroup.append(snippet_key)

            # if a summary is requested
            if summary:

                # you can pass a version into summary manually, or True
                if isinstance(summary, int):
                    summary_key = self._build_summary_key(keyname, namespace, snippet_key, summary)
                else:
                    summary_key = self._build_summary_key(keyname, namespace, snippet_key)
                keygroup.append(snippet_key)

        return keygroup

    def _build_namespace_key(self, namespace):

        ''' Build a key for a ContentNamespace '''

        # if it's not the system namespace, it's key-worthy
        if namespace != _SYSTEM_NAMESPACE:
            if not isinstance(namespace, ndb.Key):
                try:
                    namespace = ndb.Key(models.ContentNamespace, ndb.Key(urlsafe=namespace).urlsafe())
                except Exception, e:
                    namespace = ndb.Key(models.ContentNamespace, hashlib.sha256(str(namespace)).hexdigest())
        else:
            namespace = ndb.Key(models.ContentNamespace, _SYSTEM_NAMESPACE)

        return namespace

    def _build_area_key(self, keyname, namespace):

        ''' Build a key for a ContentArea '''

        if not isinstance(namespace, ndb.Key):
            namespace = self._build_namespace_key(namespace)
        if (not isinstance(keyname, basestring)) or (not isinstance(namespace, ndb.Key)):
            raise ValueError("Must pass in a string keyname and ContentNamespace-compatible Key or string namespace.")
        else:
            return ndb.Key(models.ContentArea, hashlib.sha256(str(keyname)).hexdigest(), parent=namespace)

    def _build_snippet_key(self, keyname=None, namespace=None, area=None, version=1):

        ''' Build a key for a ContentSnippet '''

        if area is not None:
            return ndb.Key(models.ContentSnippet, str(version), parent=area)
        else:
            return ndb.Key(models.ContentSnippet, str(version), parent=self._build_area_key(keyname, namespace))

    def _build_summary_key(self, keyname, namespace, snippet=None, version=1):

        ''' Build a key for a ContentSummary '''

        if snippet is not None:
            return ndb.Key(models.ContentSummary, str(version), parent=snippet)
        else:
            return ndb.Key(models.ContentSummary, str(version), parent=self._build_snippet_key(keyname, namespace))

    def _find_callblocks(self, node):

        ''' Find callblocks in a node. '''

        ## @TODO: Implement AST walking.
        raise NotImplemented

    def _walk_jinja2_ast(self, ast):

        ''' Discover the power, of the haterade '''

        ## @TODO: Implement AST walking.
        raise NotImplemented

    def _pre_ast_hook(self, template_ast):

        ''' Pre-hook that is called right after the template AST is ready '''

        ## @TODO: Preload content with a pleasant walk down the AST.
        return template_ast

    def _compiled_ast_hook(self, code):

        ''' Post-hook that is called after the AST is compiled into a <code> object '''

        ## @TODO: Pick up the hints generated by pre_ast_hook.
        return code


    ## == Mid-level Methods == ##
    def _fulfill_content_area(self, keyname, namespace, caller):

        ''' Return a contentarea's content, or the caller's default, at render time. '''

        area = self._fulfill(self._build_area_key(keyname, namespace))
        if area is None:
            return caller()

        if area.local:
            return (area.html, area.text)

        else:
            snippet = self._fulfill(area.latest)
            if snippet is None:
                return caller()
            return (snippet.html, snippet.text)

    def _fulfill_content_snippet(self, keyname, namespace, caller):

        ''' Return a contentsnippet's content, or the caller's default, at render time. '''

        area = self._fulfill(self._build_area_key(keyname, namespace))
        if area is None:
            return caller()

        snippet = self._fulfill(area.latest)
        if snippet is None:
            return caller()
        return (snippet.html, snippet.text)

    def _fulfill_content_summary(self, keyname, namespace, caller):

        ''' Return a contentsummary's content, or the caller's default, at render time. '''

        area = self._fulfill(self._build_area_key(keyname, namespace))
        if area is None:
            return caller()

        snippet = self._fulfill(area.latest)
        if snippet is None:
            return caller()

        if snippet.summary is None:
            return caller()

        summary = self._fulfill(snippet.summary)
        if summary is None:
            return caller()
        return (summary.html, summary.text)

    def _load_template(self, _environment, name, direct=False):

        ''' Load a template from source/compiled packages and preprocess. '''

        ## check the internal API bytecode cache first
        if name not in self.templates:

            # get loader + bytecacher
            loader = _environment.loader
            bytecache = _environment.bytecode_cache

            try:
                # for modules: load directly (it's way faster)
                if not loader.has_source_access:
                    template = self._pre_ast_hook(loader.load(_environment, name, prepare=False))
                    if direct:
                        return template

                    template = loader.prepare_template(_environment, name, template.run(_environment), _environment.globals)
                    self.templates[name] = template

                    return self._compiled_ast_hook(self.templates.get(name))

                # for source-based templates
                else:
                    # load template source
                    source, template, uptodate = loader.get_source(_environment, name)

                    # parse abstract syntax tree
                    if not direct:
                        parsed_ast = self._pre_ast_hook(_environment.parse(_environment.preprocess(source)))
                    else:
                        return _environment.parse(_environment.preprocess(source))

                    # check the bytecode cache for compiled source for this template
                    code = None
                    if bytecache is not None:
                        bucket = bytecache.get_bucket(_environment, name, template, source)
                        if bucket.code is not None:
                            code = bucket.code

                    # if we couldn't get it anywhere else, compile source to bytecode
                    if code is None:
                        code = _environment.compile(parsed_ast, name, template)

                        if bytecache is not None:
                            bucket.code = code
                            bytecache.set_bucket(bucket)

                    # we now have bytecode
                    self.templates[name] = code

                    if direct:
                        return code
                    else:
                        return self._compiled_ast_hook(_environment.template_class.from_code(_environment, code, _environment.globals, uptodate))

            except TemplateNotFound:
                raise

        # return from API cache
        else:
            tpl = self.templates.get(name)
            if isinstance(tpl, dict):
                return self._compiled_ast_hook(_environment.template_class.from_module_dict(_environment, tpl, _environment.globals))
            if isinstance(tpl, environment.Template):
                return tpl
            return self._compiled_ast_hook(_environment.template_class.from_code(_environment, tpl, _environment.globals, True))


    ## == High-level Methods == ##
    @toplevel
    def preload_namespace(self, namespace, snippet=True, summary=False):

        ''' Preload an entire namespace of content '''

        if not isinstance(namespace, ndb.Key):
            namespace = self._build_namespace_key(namespace)

        yield self._run_query_async(self._build_projection_query(kind=models.ContentArea, parent=namespace, properties=['l', 'lc']), count=True,
            resultset_callback=self._batch_fulfill_async, eventual_callback=self.preload_content)

    @tasklet
    def preload_content(self, areas, snippet=True, summary=False, query=None):

        ''' Preload a set of content areas asynchronously '''

        if isinstance(areas, ndb.MultiFuture):
            areas = areas.get_result()
            if len(areas) == 0:
                raise ndb.Return([])

        if not isinstance(areas, list):
            areas = [areas]

        snippet_queries = []
        for area in areas:
            snippet_queries.append(self._build_keysonly_query(kind=models.ContentSnippet, parent=area, resultset_callback=self.batch_fulfill_async, eventual_callback=self._batch_store_callback))

        query_futures = [self._run_query_async(q) for q in snippet_queries]

        ## Parrallel yield, then return!
        yield tuple(query_futures + [self._batch_store_callback(areas)])
        raise ndb.Return(None)

    def prerender(self, environment, path_or_template):

        ''' Prerender the currently selected template. '''

        # If it's a string path...
        if isinstance(path_or_template, basestring):
            template_object = self._load_template(environment, path_or_template)
        else:
            template_object = path_or_template

        return template_object

    def render(self, template, context):

        ''' Render a template, given context '''

        if template is None:
            raise ValueError('Must pass in a template object or path to template source or an iterable of those.')
        else:
            return template.render(**context)

    def fulfill(self, keyname, namespace, caller, blocktype):

        ''' Utilize the blocktype-specific method according to the template render routine and dispatch to fulfill. '''

        if blocktype not in _blocktypes:
            raise ValueError('Invalid dynamic content block type. Must be one of "%s".' % _blocktypes)
        return {

            'area': self._fulfill_content_area,
            'snippet': self._fulfill_content_snippet,
            'summary': self._fulfill_content_summary

        }.get(blocktype)(keyname, namespace, caller)


## Globals (phase II)
_output_api_instance = CoreContentAPI()


## ContentBridge - brings Core Content API functionality down into an easy mixin
class ContentBridge(object):

    ''' Mixin that bridges dynamic content methods into RemoteServices and WebHandlers. '''

    # References
    __app = None
    __handler = None
    __service = None
    __environment = None

    # Bridge state
    __content_bridge = None
    __content_prerender = None

    @webapp2.cached_property
    def config(self):

        ''' Named config pipe. '''

        return config.config.get('apptools.core.output.content.ContentBridge', {})

    @webapp2.cached_property
    def logging(self):

        ''' Named logging pipe. '''

        return debug.AppToolsLogger(path='apptools.core.output.content', name='ContentBridge')._setcondition(self.config.get('debug', True))

    @webapp2.cached_property
    def _prOutputConfig(self):

        ''' Named config pipe to output config. '''

        return self._outputConfig

    @webapp2.cached_property
    def _jinjaConfig(self):

        ''' Cached access to Jinja2 base config. '''

        return config.config.get('webapp2_extras.jinja2', {})

    @webapp2.cached_property
    def _outputConfig(self):

        ''' Cached access to base output config. '''

        return config.config.get('apptools.project.output', {})

    @webapp2.cached_property
    def _environment(self):

        ''' Cached access to the current template environment. '''

        if self.__environment is None:
            self.__environment = self.dynamicEnvironmentFactory(self.__app)
        return self.__environment

    @webapp2.cached_property
    def _webHandlerConfig(self):

        ''' Cached access to this handler's config. '''

        return config.config.get('apptools.classes.WebHandler', {})

    def _initialize_dynamic_content(self, app, handler=None, service=None, environment=None):

        ''' Initialize the content bridge from an already-instantiated Handler or Service. '''

        self.__app = app
        if handler:
            self.__handler = handler
        elif service:
            self.__service = service
            self.__handler = service.handler
        if self.__app is None:
            self.__app = self.__handler.app
        if environment:
            self.__environment = environment
        self.__acquire_content_bridge()
        return

    def __acquire_content_bridge(self):

        ''' Resolve the current instance of the CoreContentAPI, or create one. '''

        global _output_api_instance
        if self.__content_bridge is not None:
            return self.__content_bridge
        else:
            if _output_api_instance is not None:
                self.__content_bridge = _output_api_instance
            else:
                self.__content_bridge = _output_api_instance = CoreContentAPI()
        return self.__content_bridge

    def preload_template(self, template):

        ''' Preload and pre-render (pre-bytecompile) a template before rendering begins. '''

        if self.__content_bridge is None:
            self.__acquire_content_bridge()
        self.__content_prerender = self.__content_bridge.prerender(self._environment, template)
        return self.__content_prerender

    def preload_namespace(self, namespace, snippet=True, summary=False):

        ''' Preload a namespace-full of content '''

        self.__content_bridge.preload_namespace(namespace, snippet, summary)

    def dynamicEnvironmentFactory(self, app):

        ''' Prepare a Jinja2 environment suitable for rendering openfire templates. '''

        global _output_loader
        global _output_extensions
        global _output_bytecacher

        if self.__environment is not None:
            return self.__environment

        else:

            # get openfire extension config
            self.logging.info('Preparing Jinja2 OF template execution environment.')

            # use output logging condition for a minute
            self.logging._setcondition(self._prOutputConfig.get('extensions', {}).get('config', {}).get('logging', True))

            # get jinja2 base config
            j2cfg = self._jinjaConfig
            base_environment_args = j2cfg.get('environment_args')
            base_extensions_list = base_environment_args.get('extensions')

            if self._prOutputConfig.get('extensions', {}).get('config', {}).get('enabled', False) == True:

                if isinstance(_output_extensions, dict) and (len(_output_extensions) == len(base_extensions_list)):
                    compiled_extension_list = _output_extensions.values()

                else:
                    # Seen classes
                    installed_bytecaches = []
                    installed_extensions = []

                    if (len(self._webHandlerConfig.get('extensions').get('load')) + len(base_extensions_list)) > 0:
                        for name in self._webHandlerConfig.get('extensions').get('load') + base_extensions_list:
                            if name in self._prOutputConfig.get('extensions').get('installed'):
                                if self._prOutputConfig.get('extensions').get('installed').get(name).get('enabled', False) == True:
                                    extension_path = self._prOutputConfig.get('extensions').get('installed').get(name).get('path')
                                else:
                                    continue
                            else:
                                extension_path = name

                            try:
                                extension = webapp2.import_string(extension_path)

                            except ImportError:
                                self.logging.error('Encountered ImportError when trying to import extension at name "%s" and path "%s"' % (name, extension_path))

                            else:
                                if issubclass(extension, Extension):
                                    installed_extensions.append((name, extension))
                                    _output_extensions[name] = extension
                                elif issubclass(extension, BytecodeCache):
                                    installed_bytecaches.append((name, extension))

                        # combine extensions and load
                        compiled_extension_list = []
                        map(lambda x: compiled_extension_list.append(x),
                            filter(lambda x: x not in compiled_extension_list,
                                map(lambda x: isinstance(x, basestring) and webapp2.import_string(x) or x,
                                    [e for (n, e) in installed_extensions])))

                    else:
                        self.logging.warning('No extensions installed/found in config (at "openfire.output").')

            else:
                installed_bytecaches = []
                installed_extensions = []
                compiled_extension_list = []

            templates_compiled_target = j2cfg.get('compiled_path')
            if config.debug:
                if j2cfg.get('force_compiled', False) is True:
                    use_compiled = True
                else:
                    use_compiled = False
            else:
                use_compiled = True

            # resolve loader/s
            if _output_loader is not None:
                _loader = _output_loader
            else:
                if (templates_compiled_target is not None) and (use_compiled is True):
                    _loader = output.ModuleLoader(templates_compiled_target)
                else:
                    _loader = output.CoreOutputLoader(j2cfg.get('template_path'))
                _output_loader = _loader

            self.logging.info('Final extensions list: "%s".' % compiled_extension_list)
            self.logging.info('Chosen loader: "%s".' % _loader)

            # resolve bytecacher/s
            if _output_bytecacher is not None:
                _bytecacher = _output_bytecacher
            else:
                if len(installed_bytecaches) > 0:
                    _output_bytecacher = installed_bytecaches[0][1]()
                    _bytecacher = _output_bytecacher

            # bind environment args
            base_environment_args['loader'] = _loader
            base_environment_args['bytecode_cache'] = _output_bytecacher

            # hook up filters
            filters = {
                'currency': lambda x: self._format_as_currency(x, False),
                'percentage': lambda x: self._format_as_percentage(x, True),
                'json': AppToolsJSONEncoder().encode,
                'timesince': timesince.timesince,
                'humanize': byteconvert.humanize_bytes
            }

            # generate environment
            finalConfig = dict(j2cfg.items()[:])
            environment_args = finalConfig.get('environment_args', {})
            environment_args.update(base_environment_args)

            env = environment.Environment(**environment_args)

            # update globals and filters
            env.globals.update(self.__handler.baseContext)
            env.filters.update(filters)

            # patch in app, handler, ext and api
            env.extend(**{
                'wsgi_current_application': app,
                'wsgi_current_handler': self.__handler,
                'jinja2_current_loader': _loader,
                'jinja2_current_bytecache': base_environment_args.get('bytecode_cache')
            })

            for extension in compiled_extension_list:
                env.add_extension(extension)

            # replace logging conditional
            handler_config = self.__handler._webHandlerConfig
            if handler_config:
                log_condition = handler_config.get('logging', True)
            else:
                log_condition = True # default to True
            self.logging._setcondition(log_condition)
            self.__environment = env

            return self.__environment

    def render_dynamic(self, path=None, context={}, elements={}, content_type='text/html', headers={}, dependencies=[], flush=True, **kwargs):

            ''' Render shim for advanced dynamic content rendering. '''

            if not isinstance(self, webapp2.RequestHandler):
                handler = self.handler
            else:
                handler = self

            # Provide render options to template
            _render_opts = {
                'path': path,
                'self': handler,
                'context': context,
                'elements': elements,
                'content_type': content_type,
                'headers': headers,
                'dependencies': dependencies,
                'kwargs': kwargs
            }

            context['__render_opts'] = _render_opts

            # Layer on user context
            if isinstance(handler.context, dict) and len(handler.context) > 0:
                handler.context.update(context)
            else:
                handler.context = context

            # Build response headers
            for key, value in handler.baseHeaders.items():
                handler.response.headers[key] = value

            # Consider kwargs
            if len(kwargs) > 0:
                handler.context.update(kwargs)

            # Bind runtime-level template context
            handler.context = handler._bindRuntimeTemplateContext(handler.context)

            # Bind elements
            if len(elements) > 0:
                map(handler._setcontext, elements)

            # If we have a pre-render, use it, otherwise load and render
            if self.__content_prerender is not None:
                rendered = self.__content_bridge.render(self.__content_prerender, handler.context)

            else:
                # Get/select the template using our environment
                rendered = self.__content_bridge.prerender(self._environment, path).render(handler.context)

            if flush:
                # Output rendered template
                return handler.response.write(handler.minify(rendered))
            else:
                # Return rendered template
                return handler.minify(rendered)

    render = render_dynamic

    def fulfill_content(self, keyname, namespace, caller, blocktype):

        ''' Callback from template render to fulfill a dynamic content block. '''

        return self.__content_bridge.fulfill(keyname, namespace, caller, blocktype)

    def get_dynamic_namespace(self, namespace):

        ''' Retrieve or create a ContentNamespace record '''

        if namespace != _SYSTEM_NAMESPACE:
            try:
                target = ndb.Key(urlsafe=namespace)
            except:
                target = None

        namespace_key = self.__content_bridge._build_namespace_key(namespace)
        namespace_obj = namespace_key.get()
        if namespace_obj is None:
            return models.ContentNamespace(key=namespace_key, name=namespace, target=target).put()
        else:
            return namespace_obj.key

    def initialize(self, handler):

        ''' Initialize dynamic content support for an already-constructed handler. '''

        self.handler = handler
        return self._initialize_dynamic_content(handler.app, handler)
