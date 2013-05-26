# -*- coding: utf-8 -*-

"""
----------------------
apptools2: model tests
----------------------

testsuite for exercising the functions in
the apptools model API.

:author: Sam Gammon (sam@momentum.io)
:copyright: (c) 2013 momentum labs.
:license: This is private source code - Ampush has been granted an
          unlimited, exclusive license for embedded use. For details
          about embedded licenses and other legalese, see `LICENSE.md`.
"""

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
