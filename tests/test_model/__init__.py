# -*- coding: utf-8 -*-

'''

	apptools2: model tests
	-------------------------------------------------
	|												|	
	|	`apptools.tests.model` 						|
	|												|
	|	this package contains test cases and utils	|
	| 	for testing the apptools model API. 		|
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

		except ImportError as e:
			return self.fail("Failed to import concrete classes exported by Model.")

		else:
			self.assertTrue(Key)  # must export Key
			self.assertTrue(Model)  # must export Model
			self.assertTrue(Property)  # must export Property
			self.assertTrue(AbstractKey)  # must export AbstractKey
			self.assertTrue(AbstractModel)  # must export AbstractModel
			self.assertIsInstance(model, type(os))  # must be a module (lol)
