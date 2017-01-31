# -*- coding: utf-8 -*-

'''

    apptools model tests: `apptools.model`

    testsuite for exercising the functions in
    the apptools model API.

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
import os

# apptools test
from apptools.tests import AppToolsTest


## ModelExportTests
# Tests that things exported by the model package are there.
class ModelExportTests(AppToolsTest):

    ''' Tests objects exported by `model`. '''

    def test_concrete(self):

        ''' Test that we can import concrete classes. '''

        try:
            from apptools import model
            from apptools.model import Key
            from apptools.model import Model
            from apptools.model import Property
            from apptools.model import AbstractKey
            from apptools.model import AbstractModel

        except ImportError:  # pragma: no cover
            return self.fail("Failed to import concrete classes exported by Model.")

        else:
            self.assertTrue(Key)  # must export Key
            self.assertTrue(Model)  # must export Model
            self.assertTrue(Property)  # must export Property
            self.assertTrue(AbstractKey)  # must export AbstractKey
            self.assertTrue(AbstractModel)  # must export AbstractModel
            self.assertIsInstance(model, type(os))  # must be a module (lol)
