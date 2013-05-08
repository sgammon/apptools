# -*- coding: utf-8 -*-

'''

    apptools2: model key tests
    -------------------------------------------------
    |                                               |
    |   `apptools.tests.model.key`                  |
    |                                               |
    |   test cases for model classes that           |
    |   represent unique persistence keys.          |
    |                                               |
    -------------------------------------------------
    |   authors:                                    |
    |       -- sam gammon (sam@momentum.io)         |
    -------------------------------------------------
    |   changelog:                                  |
    |       -- apr 1, 2013: initial draft           |
    -------------------------------------------------

'''

# stdlib
import unittest

# apptools keys
from apptools import model
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

    def test_key_stringify(self):

        ''' Test the string representation of a `Key` object. '''

        # build and stringify key
        k = Key("SampleKind", "sample_id")
        x = str(k)

        # make sure the kind is somewhere
        self.assertTrue(("kind" in x))
        self.assertTrue(("SampleKind" in x))

        # make sure the ID is somewhere
        self.assertTrue(("id" in x))
        self.assertTrue(("sample_id" in x))

        # make sure the key class is somewhere
        self.assertTrue(('Key' in x))

    def test_key_class_stringify(self):

        ''' Test the string representation of a `Key` class. '''

        # build and stringify key
        x = str(Key)

        # make sure the kind is somewhere
        self.assertTrue(("kind" in x))

        # make sure the ID is somewhere
        self.assertTrue(("id" in x))

        # make sure the key class is somewhere
        self.assertTrue(('Key' in x))

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

    def test_key_len(self):

        ''' Test the length of a `Key`, which should only be 0 in the case of an incomplete key. '''

        k, nk = Key("Sample"), Key("Sample", "sample")

        # a key with no ID should evaluate to 0 via len()
        self.assertEqual(len(k), 0)
        self.assertEqual(len(nk), 1)

    def test_key_with_model_class_kind(self):

        ''' Test making a `Key` via using a model class as the kind. '''

        ## KindedModel
        # Used to test using classes for kinds in `model.Key`.
        class KindedModel(model.Model):

            ''' Sample for testing key creation from model classes. '''

            string = basestring

        # make keys
        k1 = model.Key("KindedModel", "test_id")
        k2 = model.Key(KindedModel, "test_id")
        ko = model.Key(KindedModel)

        # test keys
        self.assertEqual(k1.kind, "KindedModel")
        self.assertEqual(k1.id, "test_id")
        self.assertEqual(k2.kind, k1.kind)
        self.assertEqual(k2.id, k2.id)

    def test_key_ancestry(self):

        ''' Make a key with ancestry and test it a bunch. '''

        # manufacture keys
        pk = model.Key("ParentKind", "parent_id")
        ck = model.Key("ChildKind", "child_id", parent=pk)
        gk = model.Key("GrandchildKind", "grandchild_id", parent=ck)
        ggk = model.Key("GreatGrandchildKind", "great_grandchild_id", parent=gk)

        # for each key, make sure parent is set
        self.assertEqual(pk.parent, None)
        self.assertEqual(ck.parent, pk)
        self.assertEqual(gk.parent, ck)
        self.assertEqual(ggk.parent, gk)

        # for each key, make sure ancestry works
        pk_ancestry = [i for i in pk.ancestry]
        ck_ancestry = [i for i in ck.ancestry]
        gk_ancestry = [i for i in gk.ancestry]
        ggk_ancestry = [i for i in ggk.ancestry]

        # test ancestry paths
        self.assertEqual(len(pk_ancestry), 1)
        self.assertEqual(len(ck_ancestry), 2)
        self.assertEqual(len(gk_ancestry), 3)
        self.assertEqual(len(ggk_ancestry), 4)

        # len of a key should always be 1 unless it has ancestry, then it's the length of the ancestry chain
        self.assertEqual(len(pk), 1)
        self.assertEqual(len(ck), 2)
        self.assertEqual(len(gk), 3)
        self.assertEqual(len(ggk), 4)

        # ... however all keys should test nonzero-ness (all keys should be nonzero)
        for k in (pk, ck, gk, ggk):
            self.assertTrue(k)

    def test_key_with_overflowing_schema(self):

        ''' Test construction of a `Key` with too many schema items. '''

        # try and make a key with a ton of arguments
        with self.assertRaises(TypeError):
            k = model.Key("SampleKind", "id", "coolstring", "whatdowedo", "whenwehave", "thismanyarguments")

    def test_key_construct_multiple_formats(self):

        ''' Test constuction of a `Key` with multiple formats, which is not supported. '''

        # sample key
        ok = model.Key("Sample", "sample_id")

        # try and make a key with multiple formats
        with self.assertRaises(TypeError):
            model.Key(raw=ok.flatten(False)[1], urlsafe=ok.urlsafe())

    @unittest.skip("Test is not yet implemented.")
    def test_key_auto_id(self):

        ''' Test an integer-based ID field. '''

        pass  # @TODO: test auto ID's

    @unittest.skip("Test is not yet implemented.")
    def test_key_format(self):

        ''' Make sure there's a proper format spec on `model.Key`. '''

        pass  # @TODO: test __schema__

    @unittest.skip("Test is not yet implemented.")
    def test_key_set_attribute(self):

        ''' Try setting an unknown and known attribute. '''

        pass  # @TODO: test __setattr__

    @unittest.skip("Test is not yet implemented.")
    def test_key_adapter(self):

        ''' Make sure the adapter is attached correctly to `model.Key`. '''

        pass  # @TODO: test __adapter__
