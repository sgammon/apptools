# -*- coding: utf-8 -*-

"""

Core: Output

Responsible for the task of finding and compiling templates to be sent to the browser.
Two levels of caching are implemented here - in-memory handler caching and memcache.

According to settings in the config.py, this module will attempt to load compiled
template code from the handler first, memcache second, and at last resort will compile
the template and store it in the cache.

-sam (<sam@momentum.io>)

"""

## Base Imports
import os
import base64
import pprint
import config
import random
import logging
import datetime

## Bootstrap Routine
try:
	import bootstrap
	bootstrap.AppBootstrapper.prepareImports()
except ImportError:
	logging.warning('Could not execute app bootstrapper.')
	pass

from os import path
from os.path import getmtime

## AppTools
from apptools import AppException

## Webapp2 Imports
from webapp2 import cached_property
from webapp2_extras.jinja2 import Jinja2

## Jinja2 Imports
from jinja2 import Environment as JEnvironment
from jinja2 import ModuleLoader as JModuleLoader
from jinja2 import FileSystemLoader as JFileSystemLoader
from jinja2.exceptions import TemplateNotFound


## Output Exception
class CoreOutputAPIException(AppException):
	pass


class ModuleLoader(object):
	
	''' Loads templates that have been compiled into Python modules. '''
	
	def __init__(self, templatemodule):
	
		''' Loads a template from a module. '''
		
		self.modules = {}
		self.templatemodule = templatemodule

	def load(self, environment, filename, globals=None):

		''' Loads a pre-compiled template, stored as Python code in a template module. '''

		if globals is None:
			globals = {}

		# Strip '/' and remove extension.
		filename, ext = path.splitext(filename.strip('/'))

		if filename not in self.modules:
			# Store module to avoid unnecessary repeated imports.
			self.modules[filename] = self.get_module(environment, filename)

		tpl_vars = self.modules[filename].run(environment)

		t = object.__new__(environment.template_class)
		t.environment = environment
		t.globals = globals
		t.name = tpl_vars['name']
		t.filename = filename
		t.blocks = tpl_vars['blocks']

		# render function and module
		t.root_render_func = tpl_vars['root']
		t._module = None

		# debug and loader helpers
		t._debug_info = tpl_vars['debug_info']
		t._uptodate = lambda: True

		return t

	def get_module(self, environment, template):
		
		''' Converts a template path to a package path and attempts import, or else raises Jinja2's TemplateNotFound. '''
		
		# Convert the path to a module name.
		module_name = self.templatemodule + '.' + template.replace('/', '.')
		prefix, obj = module_name.rsplit('.', 1)

		try:
			return getattr(__import__(prefix, None, {'environment': environment}, [obj]), obj)
		except (ImportError, AttributeError):
			raise TemplateNotFound(template)


# Source caching
def get_tdata_from_fastcache(name, do_log):

	''' Get template data from fastcache (instance memory). '''

	if name in t_data:
		if do_log: logging.debug('OUTPUT_LOADER: Found bytecode in fastcache memory under key \''+str(base64.b64encode(name))+'\'.')
		return t_data[name]
	else: return None
	
def set_tdata_to_fastcache(name, data, do_log):
	
	''' Save template data to fastcache (instance memory). '''
	
	t_data[name] = data
	if do_log: logging.debug('OUTPUT_LOADER: Set template \''+str(name)+'\' to fastcache memory.')
	

# Memcache API loader
def get_tdata_from_memcache(name, do_log):
	
	''' Get template data from memcache. '''
	
	data = memcache.get('Core//Output//Template-'+name)
	if data is not None:
		if do_log: logging.debug('OUTPUT_LOADER: Found bytecode in memcache under key \'tdata-'+str(name)+'\'.')
		return data
	else: return None
	
def set_tdata_to_memcache(name, data, do_log):
	
	''' Set template data to memcache. '''
	
	memcache.set('Core//Output//Template-'+name, data)
	if do_log: logging.debug('OUTPUT_LOADER: Set template \''+str(name)+'\' to memcache under key \'Core//Output//Template-'+str(name)+'\'.')
	

# Loader class
class CoreOutputLoader(JFileSystemLoader):
	
	''' Loads templates and automatically inserts bytecode caching logic for both fastcache (instance memory) and memcache. '''
	
	@cached_property
	def devConfig(self):
		
		''' Cached dev configuration. '''
		
		return config.config.get('apptools.system.dev')
		
	@cached_property
	def loaderConfig(self):
		
		''' Cached template loader configuration. '''
		
		return config.config.get('apptools.project.output.template_loader')

	def get_source(self, environment, name):
		
		''' Overrides Jinja's default FileSystemLoader get_source to provide it via memcache or instance memory, if available. '''

		# Load config
		dev = self.devConfig
		y_cfg = self.loaderConfig
		
		# Encode in Base64
		b64_name = base64.b64encode(name)

		# Debug logging
		if y_cfg.get('debug') == True: do_log = True
		else: do_log = False
		if do_log: logging.debug('OUTPUT_LOADER: Template Loader received request for name \''+str(name)+'\'.')
		
		# Don't do caching if we're in dev mode
		if not config.debug or self.loaderConfig['force'] is True:

			# Try the in-memory supercache
			if y_cfg.get('use_memory_cache') == True: source = get_tdata_from_fastcache(b64_name, do_log)
			else: source = None
		
			if source is None: # Not found in fastcache
		
				if do_log: logging.debug('OUTPUT_LOADER: Template not found in fastcache.')
			
				# Fallback to memcache
				if y_cfg.get('use_memcache') == True: source = get_tdata_from_memcache(b64_name, do_log)

				# Fallback to regular loader, then cache
				if source is None: # Not found in memcache
				
					if do_log: logging.debug('OUTPUT_LOADER: Template not found in memcache.')
					source, name, uptodate = super(CoreOutputLoader, self).get_source(environment, name)
				
					if y_cfg.get('use_memcache') != False:
						set_tdata_to_memcache(b64_name, source, do_log)
				
					if y_cfg.get('use_memory_cache') != False:
						set_tdata_to_fastcache(b64_name, source, do_log)
	
		else: ## In dev mode, compile everything every time
		
			source, name, uptodate = super(CoreOutputLoader, self).get_source(environment, name)
			return source, name, uptodate
			
		# Return compiled template code
		return source, name, lambda: True