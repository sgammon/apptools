# -*- coding: utf-8 -*-

'''

	apptools2: model key tests
	-------------------------------------------------
	|												|	
	|	`apptools.tests.model.key`					|
	|												|
	|	test cases for model classes that			|
	|	represent unique persistence keys. 			|
	|												|	
	-------------------------------------------------
	|	authors:									|
	|		-- sam gammon (sam@momentum.io)			|
	-------------------------------------------------	
	|	changelog:									|
	|		-- apr 1, 2013: initial draft			|
	-------------------------------------------------

'''

# apptools keys
from apptools.model import Key
from apptools.model import AbstractKey

# apptools tests
from apptools.tests import AppToolsTest


## KeyTests
# Tests that the Key class works properly.
class KeyTests(AppToolsTest):

	''' Tests `model.Key` and `model.AbstractKey`. '''

	def test_construct_key(self):

		''' Try constructing a key manually. '''

		# test kinded empty key
		k = Key("TestKind")
		self.assertEqual(k.kind, "TestKind")

		# test kinded ID'd key
		k = Key("TestKind", "sample")
		self.assertEqual(k.kind, "TestKind")
		self.assertEqual(k.id, "sample")

		# test parented, kinded ID'd key
		pk = Key("TestParentKind", "parent")
		k = Key("TestKind", "child", parent=pk)
		self.assertEqual(k.kind, "TestKind")
		self.assertEqual(k.id, "child")
		self.assertEqual(k.parent, pk)

		# make sure basic properties are ok
		self.assertEqual(k.__slots__, set())
		self.assertEqual(k.__class__.__name__, "Key")
		self.assertEqual(k.__class__.__slots__, set())

	def test_key_inheritance(self):

		''' Make sure there's a proper inheritance structure for `model.Key`. '''

		# test basic key inheritance
		k = Key("TestKind", "sample")

		# test basic inheritance
		self.assertIsInstance(k, Key)
		self.assertIsInstance(k, AbstractKey)
		self.assertIsInstance(k, object)

		# test class inheritance
		self.assertTrue(issubclass(Key, AbstractKey))
		self.assertTrue(AbstractKey in Key.__bases__)
		self.assertIsInstance(Key, AbstractKey.__metaclass__)

		# check `AbstractKey` inheritance
		self.assertTrue(type(k) == Key)
		self.assertTrue(issubclass(Key, object))

	def test_key_format(self):

		''' Make sure there's a proper format spec on `model.Key`. '''

		pass  # @TODO: test __schema__

	def test_key_set_attribute(self):

		''' Try setting an unknown and known attribute. '''

		pass  # @TODO: test __setattr__

	def test_key_adapter(self):

		''' Make sure the adapter is attached correctly to `model.Key`. '''

		pass  # @TODO: test __adapter__

	def test_key_stringify(self):

		''' Test the string representation of a Key object. '''

		pass  # @TODO: test __repr__()

	def test_key_auto_id(self):

		''' Test an integer-based ID field. '''

		pass  # @TODO: test auto ID's

	def test_namespace(self):

		''' Test a namespaced Key. '''

		pass  # @TODO: test namespacing

	def test_abstract_key(self):

		''' Make sure `model.AbstractKey` works abstractly. '''

		# should not be able to instantiate `AbstractKey`
		with self.assertRaises(TypeError):
			k = AbstractKey()

		self.assertIsInstance(Key(), AbstractKey)

	def test_concrete_key(self):

		''' Make sure `model.Key` works concretely. '''

		# sample `Key` subclass
		class SampleKey(Key):
			''' Tests subclasses of `Key`. '''
			__schema__ = tuple(['id', 'kind'])

		# perform tests
		self.assertTrue(SampleKey("Sample", "id"))
		self.assertIsInstance(SampleKey("Sample", "id"), Key)
		self.assertTrue(hasattr(SampleKey, '__schema__'))
		self.assertEqual(len(SampleKey.__schema__), 2)

	def test_raw_key_format(self):

		''' Try constructing a key from a raw iterable. '''

		# sample key
		k = Key("Sample", "sample")

		# tupled raw
		self.assertEqual(Key(raw=k.flatten()), k)
		self.assertEqual(Key.from_raw(k.flatten()), k)

		# joined raw
		joined, struct = k.flatten(True)
		self.assertEqual(Key(raw=joined), k)
		self.assertEqual(Key.from_raw(joined), k)

	def test_json_key_format(self):

		''' Try constructing a key from JSON. '''

		pass  # @TODO: JSON functionality

	def test_urlsafe_key_format(self):

		''' Try constructing a key from its URL-encoded form. '''

		# sample key
		k = Key("Sample", "sample")

		# urlsafe in & out
		self.assertEqual(Key(urlsafe=k.urlsafe()), k)
		self.assertEqual(Key.from_urlsafe(k.urlsafe()), k)

	def test_key_flatten(self):

		''' Try flattening a Key into a raw iterable. '''

		# sample key
		k = Key("Sample", "sample")

		# flatten in & out
		self.assertEqual(Key(raw=k.flatten()), k)
		self.assertEqual(Key.from_raw(k.flatten()), k)

	def test_key_nonzero(self):

		''' Test nonzero functionality in a key. '''

		# sample zero key and nonzero key
		k, nk = Key("Sample"), Key("Sample", "sample")

		# key with no ID should evaluate to falsy
		self.assertTrue(nk)
		self.assertTrue(not k)