# -*- coding: utf-8 -*-

'''

    apptools2: core adapter tests
    -------------------------------------------------
    |                                               |
    |   `apptools.tests.model.adapter.core`         |
    |                                               |
    |   this package contains test cases for the    |
    |   builtin core adapters (JSON/dict/etc).      |
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
import datetime

# apptools test
from apptools.tests import AppToolsTest

# apptools model API
from apptools import model
from apptools.model import adapter


## Car
# Test submodel.
class Car(model.Model):

    ''' Test submodel for key encoding tests. '''

    make = basestring, {'indexed': True}
    model = basestring, {'indexed': True}
    year = int, {'indexed': True, 'choices': xrange(1901, 2013)}
    color = basestring, {'indexed': True, 'choices': ('white', 'black', 'blue', 'yellow', 'red')}


## Person
# Test model that implements a bunch of basetypes.
class Person(model.Model):

    ''' Test model implementing all basetypes. '''

    firstname = basestring, {'indexed': True}
    lastname = basestring, {'indexed': True, 'required': True}
    age = int, {'indexed': True, 'choices': xrange(18, 99)}
    active = bool, {'indexed': True, 'default': False}
    birthday = datetime.date, {'indexed': True}
    modified = datetime.datetime, {'indexed': True, 'valid': lambda x: datetime.datetime.now()}
    created = datetime.datetime, {'indexed': True, 'default': lambda x: datetime.datetime.now()}
    cars = Car, {'repeated': True, 'indexed': True}


## CoreAdapterTests
# Tests builtin core model adapters (JSON/dict/msgpack).
class CoreAdapterTests(AppToolsTest):

    ''' Tests `model.adapter.core`. '''

    @unittest.skip("Test is not yet implemented.")
    def test_model_dict_update(self):

        ''' Test `Model.update`, which is provided by `DictMixin`. '''

        pass  # @TODO: Fill out this test.

    @unittest.skip("Test is not yet implemented.")
    def test_model_schema_to_dict(self):

        ''' Test `Model.to_schema_dict`, which is provided by `DictMixin`. '''

        pass  # @TODO: Fill out this test.

    @unittest.skip("Test is not yet implemented.")
    def test_model_schema_to_json(self):

        ''' Test `Model.to_json_schema`, which is provided by `JSONMixin`. '''

        pass  # @TODO: Fill out this test.

    @unittest.skip("Test is not yet implemented.")
    def test_model_to_msgpack(self):

        ''' Test `Model.to_msgpack`, which is provided by `MsgpackMixin`, if supported. '''

        pass  # @TODO: Fill out this test.

    @unittest.skip("Test is not yet implemented.")
    def test_model_schema_to_msgpack(self):

        ''' Test `Model.to_msgpack_schema`, which is provided by `MsgpackMixin`, if supported. '''

        pass  # @TODO: Fill out this test.
