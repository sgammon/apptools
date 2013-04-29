# -*- coding: utf-8 -*-

'''

    apptools2: in-memory adapter tests
    -------------------------------------------------
    |                                               |
    |   `apptools.tests.model.adapter.inmemory`     |
    |                                               |
    |   this package contains test cases for the    |
    |   builtin in-memory model adapter.            |
    |                                               |
    -------------------------------------------------
    |   authors:                                    |
    |       -- sam gammon (sam@momentum.io)         |
    -------------------------------------------------
    |   changelog:                                  |
    |       -- apr 1, 2013: initial draft           |
    -------------------------------------------------

'''

# apptools test
from apptools.tests import AppToolsTest

# apptools model API
from apptools import model
from apptools.model import adapter
from apptools.model.adapter import inmemory


## InMemoryModel
# Explicitly uses the builtin `InMemory` model adapter.
class InMemoryModel(model.Model):

    ''' Test model. '''

    __adapter__ = inmemory.InMemoryAdapter

    string = basestring, {'required': True}
    integer = int, {'repeated': True}


## InMemoryAdapterTests
# Tests the `InMemory` model adapter.
class InMemoryAdapterTests(AppToolsTest):

    ''' Tests `model.adapter.inmemory`. '''

    def test_invalid_get(self):

        ''' Test requesting a key that doesn't exist. '''

        # get missing entity
        model_key = model.Key("Sample", "_____")
        entity = model_key.get()
        self.assertEqual(entity, None)

    def test_named_entity_get_put(self):
        
        ''' Test putting and getting an entity with a named key. '''

        # put entity
        m = InMemoryModel(key=model.Key(InMemoryModel.kind(), "NamedEntity"), string="suphomies", integer=[4, 5, 6, 7])
        m_k = m.put()

        self.assertTrue((m_k.urlsafe() in inmemory._metadata['lookup']))

        # simulate getting entity
        explicit_key = model.Key(InMemoryModel.kind(), "NamedEntity")
        entity = explicit_key.get()

        # make sure things match
        self.assertEqual(entity.string, "suphomies")
        self.assertEqual(len(entity.integer), 4)
        self.assertEqual(entity.key.id, "NamedEntity")
        self.assertEqual(entity.key.kind, InMemoryModel.kind())

    def test_id_entity_get_put(self):

        ''' Test putting and getting an entity with an ID'd key. '''

        # put entity
        m = InMemoryModel(string="hello", integer=[1, 2, 3])
        m_k = m.put()

        self.assertTrue((m_k.urlsafe() in inmemory._metadata['lookup']))

        # make sure flags match
        self.assertEqual(m_k, m.key)
        self.assertTrue(m_k.__persisted__)
        self.assertTrue(m.__persisted__)
        self.assertTrue((not m.__dirty__))

        # simulate getting entity via urlsafe
        explicit_key = model.Key.from_urlsafe(m_k.urlsafe())
        entity = explicit_key.get()

        # make sure things match
        self.assertEqual(entity.string, "hello")
        self.assertEqual(len(entity.integer), 3)
        self.assertEqual(entity.key.kind, InMemoryModel.kind())

    def test_delete_existing_entity(self):

        ''' Test deleting an existing entity. '''

        # put entity
        m = InMemoryModel(string="hello", integer=[1, 2, 3])
        m_k = m.put()

        # make sure it's known
        self.assertTrue((m_k.urlsafe() in inmemory._metadata['lookup']))

        # delete it
        res = m_k.delete()

        # make sure it's unknown and gone
        self.assertTrue(res)
        self.assertTrue((m_k.urlsafe() not in inmemory._metadata['lookup']))

    def test_delete_invalid_entity(self):

        ''' Test deleting an invalid entity. '''

        # manufacture a key that shouldn't exist...
        m_k = model.Key("SampleKind", "____InvalidKey____")

        # make sure it's unknown
        self.assertTrue((m_k.urlsafe() not in inmemory._metadata['lookup']))

        # delete it
        res = m_k.delete()

        # make sure it's unknown, and we couldn't delete it
        self.assertTrue((not res))
        self.assertTrue((m_k.urlsafe() not in inmemory._metadata['lookup']))

    def test_allocate_ids(self):

        ''' Allocate one and numerous ID's. '''

        # try allocating one ID
        next = inmemory.InMemoryAdapter.allocate_ids("Sample", 1)
        self.assertIsInstance(next, int)

        # try allocating 10 ID's
        next_range = [i for i in inmemory.InMemoryAdapter.allocate_ids(model.Key, "Sample", 10)()]
        self.assertEqual(len(next_range), 10)
        for i in next_range:
            self.assertIsInstance(i, int)
