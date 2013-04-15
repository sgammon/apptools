# -*- coding: utf-8 -*-

'''

	apptools2: model adapter tests
	-------------------------------------------------
	|												|	
	|	`apptools.tests.model.adapters`				|
	|												|
	|	this package contains test cases and utils	|
	| 	for testing the apptools model adapter API. |
	|												|	
	-------------------------------------------------
	|	authors:									|
	|		-- sam gammon (sam@momentum.io)			|
	-------------------------------------------------	
	|	changelog:									|
	|		-- apr 1, 2013: initial draft			|
	-------------------------------------------------

'''

# stdlib
import os

# apptools test
from apptools.tests import AppToolsTest

# apptools model API
from apptools import model


## AdapterExportTests
# Tests that things exported by the model adapter package are there.
class AdapterExportTests(AppToolsTest):

	''' Tests objects exported by `model.adapter`. '''

	def test_top_level_adapter_exports(self):

		''' Test that we can import concrete classes. '''

		try:
			from apptools import model
			from apptools.model import adapter

		except ImportError as e:  # pragma: no cover
			return self.fail("Failed to import model adapter package.")

		else:
			self.assertIsInstance(adapter, type(os))  # `adapter` module
			self.assertIsInstance(adapter.abstract, type(os))  # `adapter.abstract` export
			self.assertTrue(adapter.ModelAdapter)  # `ModelAdapter` parent class
			self.assertIsInstance(adapter.abstract_adapters, tuple)  # abstract adapter list
			self.assertTrue(adapter.IndexedModelAdapter)  # `IndexedModelAdapter` subclass
			self.assertIsInstance(adapter.sql, type(os))  # `sql` adapter
			self.assertIsInstance(adapter.redis, type(os))  # `redis` adapter
			self.assertIsInstance(adapter.mongo, type(os))  # `mongo` adapter
			self.assertIsInstance(adapter.protorpc, type(os))  # `protorpc` adapter
			self.assertIsInstance(adapter.pipeline, type(os))  # `pipeline` adapter
			self.assertIsInstance(adapter.memcache, type(os))  # `memcache` adapter
			self.assertIsInstance(adapter.inmemory, type(os))  # `inmemory` adapter
			self.assertIsInstance(adapter.modules, tuple)  # full modules tuple
			self.assertTrue(issubclass(adapter.SQLAdapter, adapter.ModelAdapter))  # SQL adapter
			self.assertTrue(issubclass(adapter.RedisAdapter, adapter.ModelAdapter))  # Redis adapter
			self.assertTrue(issubclass(adapter.MongoAdapter, adapter.ModelAdapter))  # Mongo adapter
			self.assertTrue(issubclass(adapter.ProtoRPCAdapter, adapter.ModelAdapter))  # ProtoRPC adapter
			self.assertTrue(issubclass(adapter.PipelineAdapter, adapter.ModelAdapter))  # Pipeline adapter
			self.assertTrue(issubclass(adapter.MemcacheAdapter, adapter.ModelAdapter))  # Memcache adapter
			self.assertTrue(issubclass(adapter.InMemoryAdapter, adapter.ModelAdapter))  # InMemory adapter


## ModelAdapterTests
# Test `ModelAdapter`, the abstract parent class to all model adapters.
class ModelAdapterTests(AppToolsTest):

	''' Test `adapter.abstract.ModelAdapter`. '''

	def test_adapter_registry(self):

		''' Test `adapter.abstract.ModelAdapter.registry`. '''

		from apptools.model.adapter import abstract

		self.assertTrue(hasattr(abstract.ModelAdapter, 'registry'))
		self.assertIsInstance(abstract.ModelAdapter.registry, dict)

		# grab initial length of model class registry
		initlength = len(abstract.ModelAdapter.registry)

		## SampleModel
		# Quick sample model to make sure class registration happens properly.
		class Sample(model.Model):

			''' Quick sample model. '''

			pass

		# test that our class was registered
		self.assertTrue(len(abstract.ModelAdapter.registry) == (initlength + 1))
		self.assertTrue(('Sample' in abstract.ModelAdapter.registry))
		self.assertTrue(abstract.ModelAdapter.registry.get('Sample') == Sample)

	def test_default_adapter(self):

		''' Test that the default adapter is assigned properly. '''

		from apptools.model import adapter
		from apptools.model.adapter import abstract

		## TestDefault
		# Quick sample model to test default adapter injection.
		class TestDefault(model.Model):

			''' Quick sample model. '''

			pass

		# test attribute + default injector
		self.assertTrue(hasattr(TestDefault, '__adapter__'))
		self.assertIsInstance(TestDefault.__adapter__, adapter.InMemoryAdapter)

	def test_explicit_adapter(self):

		''' Test that an adapter can be set explcitly. '''

		from apptools.model import adapter
		from apptools.model.adapter import abstract

		## TestExplicit
		# Quick sample model to test explicit adapter injection.
		class TestExplicit(model.Model):

			''' Quick sample model. '''

			__adapter__ = adapter.RedisAdapter

		# test attribute + explicit injector
		self.assertTrue(hasattr(TestExplicit, '__adapter__'))
		self.assertIsInstance(TestExplicit.__adapter__, adapter.RedisAdapter)
