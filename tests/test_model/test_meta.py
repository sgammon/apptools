# -*- coding: utf-8 -*-

'''

	apptools2: meta model tests
	-------------------------------------------------
	|												|	
	|	`apptools.tests.model.meta`					|
	|												|
	|	test cases for the `model.MetaFactory`,		|
	|	which acts as an abstract metaclass that	|
	| 	provides common methods to other meta 		|
	| 	actors in the model API. 					|
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

	def test_abstract(self):

		''' Make sure `model.MetaFactory` is only usable abstractly. '''

		# constructing metafactory should raise an ABC exception
		self.assertTrue(inspect.isabstract(MetaFactory))
		with self.assertRaises(NotImplementedError):
			a = MetaFactory()

	def test_enforce(self):

		''' Define a class that violates enforced abstraction rules. '''

		class InsolentClass(MetaFactory):

			''' Look at me! I extend without implementing. The nerve! '''

			# intentionally not defined: def classmethod(initialize())
			pass

		with self.assertRaises(TypeError):
			c = InsolentClass(InsolentClass.__name__, (MetaFactory, type), dict([(k, v) for k, v in InsolentClass.__dict__.items()]))

	def test_resolve(self):

		''' Make sure `model.MetaFactory` resolves adapters correctly. '''

		# test that resolve exists
		self.assertTrue(inspect.ismethod(MetaFactory.resolve))
		self.assertIsInstance(MetaFactory.resolve(model.Model.__name__, model.Model.__bases__, model.Model.__dict__, False), tuple)
		self.assertIsInstance(MetaFactory.resolve(model.Model.__name__, model.Model.__bases__, model.Model.__dict__, True), adapter.ModelAdapter)
