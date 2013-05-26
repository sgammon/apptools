# -*- coding: utf-8 -*-

"""
---------------------------
apptools2: model meta tests
---------------------------

makes sure that abstract classes work abstractly,
and not concretely. also makes sure that concrete
classes can be extended and construct properly.

:author: Sam Gammon (sam@momentum.io)
:copyright: (c) 2013 momentum labs.
:license: This is private source code - Ampush has been granted an
          unlimited, exclusive license for embedded use. For details
          about embedded licenses and other legalese, see `LICENSE.md`.
"""

# stdlib
import inspect

# apptools model API
from apptools import model
from apptools.model import adapter
from apptools.model import MetaFactory

# apptools tests
from apptools.tests import AppToolsTest


## MetaFactoryTests
# Test the `MetaFactory` class.
class MetaFactoryTests(AppToolsTest):

    ''' Tests `model.MetaFactory`. '''

    def test_abstract_factory(self):

        ''' Make sure `model.MetaFactory` is only usable abstractly. '''

        # constructing metafactory should raise an ABC exception
        self.assertTrue(inspect.isabstract(MetaFactory))
        with self.assertRaises(NotImplementedError):
            MetaFactory()

    def test_abstract_enforcement(self):

        ''' Define a class that violates enforced abstraction rules. '''

        class InsolentClass(MetaFactory):

            ''' Look at me! I extend without implementing. The nerve! '''

            # intentionally not defined: def classmethod(initialize())
            pass

        with self.assertRaises(TypeError):
            InsolentClass(InsolentClass.__name__, (MetaFactory, type), dict([(k, v) for k, v in InsolentClass.__dict__.items()]))

    def test_resolve_adapters(self):

        ''' Make sure `model.MetaFactory` resolves adapters correctly. '''

        # test that resolve exists
        self.assertTrue(inspect.ismethod(MetaFactory.resolve))
        self.assertIsInstance(MetaFactory.resolve(model.Model.__name__, model.Model.__bases__, model.Model.__dict__, False), tuple)
        self.assertIsInstance(MetaFactory.resolve(model.Model.__name__, model.Model.__bases__, model.Model.__dict__, True), adapter.ModelAdapter)
