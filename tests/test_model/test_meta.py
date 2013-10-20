# -*- coding: utf-8 -*-

'''

    apptools model tests: `apptools.model` meta

    makes sure that abstract classes work abstractly,
    and not concretely. also makes sure that concrete
    classes can be extended and construct properly.

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
