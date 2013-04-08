# -*- coding: utf-8 -*-

'''

	apptools2: model tests
	-------------------------------------------------
	|												|	
	|	`apptools.tests.model.model`				|
	|												|
	|	test cases for the `model.Model` class, 	|
	|	which provides python data modelling.		|
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
import abc
import json
import inspect

# apptools model API
from apptools import model
from apptools.model import adapter

# apptools tests
from apptools.tests import AppToolsTest

# apptools utils
from apptools.util import datastructures


## == Test Models == ##

## Car
# Simple model simulating a car.
class Car(model.Model):

	''' An automobile. '''

	make = basestring, {'indexed': True}
	model = basestring, {'indexed': True}
	year = int, {'choices': xrange(1900, 2015)}
	color = basestring, {'choices': ('blue', 'green', 'red', 'silver', 'white', 'black')}


## Person
# Simple model simulating a person.
class Person(model.Model):

	''' A human being. '''

	firstname = basestring
	lastname = basestring
	active = bool, {'default': True}
	cars = Car, {'repeated': True}


## ModelTests
# Tests that the Model class works properly.
class ModelTests(AppToolsTest):

	''' Tests `model.Model` and `model.AbstractModel`. '''

	def test_construct_model(self):

		''' Try constructing a Model manually. '''

		# construct our car record
		car = Car(make='BMW', model='M3', year=2013, color='white')

		# construct our person record
		person = Person()
		person.firstname = 'John'
		person.cars = [car]

		# perform tests
		self.assertIsInstance(car, Car)
		self.assertIsInstance(person, Person)
		self.assertEqual(person.firstname, 'John')
		self.assertIsInstance(person.cars, list)
		self.assertEqual(len(person.cars), 1)
		self.assertIsInstance(person.cars[0], Car)

		# test defaults
		self.assertEqual(person.active, True)

		# test unsets
		self.assertEqual(person.lastname, None)

	def test_model_inheritance(self):

		''' Make sure there's a proper inheritance structure for `model.Model`. '''

		self.assertTrue(issubclass(Car, model.Model))
		self.assertTrue(issubclass(Person, model.Model))
		self.assertTrue(issubclass(model.Model, model.AbstractModel))

	def test_model_schema(self):

		''' Make sure there's a proper schema spec on `model.Model`. '''

		# check lookup
		self.assertTrue(hasattr(Person, '__lookup__'))
		self.assertIsInstance(Person.__lookup__, frozenset)

		# check property descriptors
		self.assertTrue(hasattr(Person, 'firstname'))
		self.assertTrue(hasattr(Person, 'lastname'))
		self.assertTrue(hasattr(Person, 'cars'))

		# check kind
		self.assertTrue(hasattr(Person, 'kind'))
		self.assertIsInstance(Person.kind(), basestring)

		# check set/get
		self.assertTrue(hasattr(Person, '_get_value'))
		self.assertTrue(hasattr(Person, '_set_value'))
		self.assertTrue(inspect.ismethod(Person._get_value))
		self.assertTrue(inspect.ismethod(Person._set_value))

		# check key
		self.assertTrue(hasattr(Person, 'key'))
		self.assertTrue(hasattr(Person, '__key__'))

	def test_model_set_attribute(self):

		''' Try setting an unknown and known attribute. '''

		# try construction assignment
		john = Person(firstname='John')
		self.assertEqual(john.firstname, 'John')

		# re-assign
		john.firstname = 'Blabs'
		self.assertEqual(john.firstname, 'Blabs')

		# try assigning missing property
		with self.assertRaises(AttributeError):
			john.blabs = 'John'

	def test_model_adapter(self):

		''' Make sure the adapter is attached correctly to `model.Model`. '''

		# make sure it's on the classlevel
		self.assertTrue(hasattr(Person, '__adapter__'))
		self.assertIsInstance(Person.__adapter__, adapter.ModelAdapter)

	def test_model_stringify(self):

		''' Test the string representation of a Model object. '''

		self.assertIsInstance(Person().__repr__(), basestring)

	def test_model_kind(self):

		''' Make sure the `Model.kind` is properly set. '''

		# test class-level kind
		self.assertIsInstance(Person.kind(), basestring)
		self.assertEqual(Person.kind(), "Person")

		# test object-level kind
		john = Person()
		self.assertIsInstance(john.kind(), basestring)
		self.assertEqual(john.kind(), "Person")

	def test_abstract_model(self):

		''' Make sure `model.AbstractModel` works abstractly. '''

		# make sure it's ABC-enabled
		self.assertTrue((not isinstance(model.Model, abc.ABCMeta)))

		# try directly-instantiation
		with self.assertRaises(TypeError):
			m = model.AbstractModel()

	def test_concrete_model(self):

		''' Make sure `model.Model` works concretely. '''

		## test simple construction
		self.assertIsInstance(Person(), Person)

		## test direct subclass inheritance
		class SampleModel(model.Model): parent = basestring
		class SampleSubModel(SampleModel): child = basestring

		## test properties
		self.assertTrue(hasattr(SampleModel, 'parent'))
		self.assertTrue((not hasattr(SampleModel, 'child')))

		## test submodel properties
		self.assertTrue(hasattr(SampleSubModel, 'child'))
		self.assertTrue(hasattr(SampleSubModel, 'parent'))

		## test recursive subclassing
		self.assertIsInstance(SampleModel(), model.Model)
		self.assertIsInstance(SampleSubModel(), SampleModel)
		self.assertIsInstance(SampleSubModel(), model.Model)

	def test_model_to_dict(self, method='to_dict'):

		''' Try flattening a Model into a raw dictionary. '''

		# sample person
		p = Person(firstname='John')
		raw_dict = getattr(p, method)()

		if method == 'to_dict':
			# try regular to_dict
			self.assertEqual(len(raw_dict), 2)
			self.assertIsInstance(raw_dict, dict)
			self.assertEqual(raw_dict['firstname'], 'John')  # we set this explicitly
			self.assertEqual(raw_dict['active'], True)  # this is defaulted, should export

			with self.assertRaises(KeyError):
				raw_dict['lastname']
		return raw_dict

	def test_model_to_dict_all_arguments(self, method='to_dict'):

		''' Try using `Model.to_dict` with the `all` flag. '''

		# sample person
		p = Person(firstname='John')
		all_dict = getattr(p, method)(_all=True)

		if method == 'to_dict':
			# test dict with `all`
			self.assertEqual(len(all_dict), len(p.__lookup__))
			self.assertEqual(all_dict['firstname'], 'John')
			self.assertEqual(all_dict['lastname'], None)
			self.assertEqual(all_dict['active'], True)
		return all_dict

	def test_model_to_dict_with_filter(self, method='to_dict'):

		''' Try using `Model.to_dict` with a filter function. '''

		# sample person
		p = Person(firstname='John')
		filtered_dict = getattr(p, method)(filter=lambda x: len(x[0]) > 7)  # should filter out 'active'

		if method == 'to_dict':
			# test filter
			self.assertEqual(len(filtered_dict), 1)
			self.assertIsInstance(filtered_dict, dict)
			self.assertEqual(filtered_dict['firstname'], 'John')

			with self.assertRaises(KeyError):
				filtered_dict['active']
		return filtered_dict

	def test_model_to_dict_with_include(self, method='to_dict'):

		''' Try using `Model.to_dict` with an inclusion list. '''

		# sample person
		p = Person(firstname='John')
		included_dict = getattr(p, method)(include=('firstname', 'lastname'))

		if method == 'to_dict':
			# test include
			self.assertEqual(len(included_dict), 2)  # should still include `lastname` as 'None'
			self.assertIsInstance(included_dict, dict)
			self.assertEqual(included_dict['firstname'], 'John')
			self.assertEqual(included_dict['lastname'], None)

			with self.assertRaises(KeyError):
				included_dict['active']  # should not include `active`
		return included_dict

	def test_model_to_dict_with_exclude(self, method='to_dict'):

		''' Try using `Model.to_dict` with an exclusion list. '''

		# sample person
		p = Person(firstname='John')
		excluded_dict = getattr(p, method)(exclude=('active',))

		if method == 'to_dict':
			# test exclude
			self.assertEqual(len(excluded_dict), 1)
			self.assertIsInstance(excluded_dict, dict)
			self.assertEqual(excluded_dict['firstname'], 'John')

			with self.assertRaises(KeyError):
				excluded_dict['active']  # should not include `active`
		return excluded_dict

	def test_model_to_dict_with_map(self, method='to_dict'):

		''' Try using `Model.to_dict` with a map function. '''

		# sample person
		p = Person(firstname='John')
		mapped_dict = getattr(p, method)(map=lambda x: tuple([x[0] + '-cool', x[1]]))

		if method == 'to_dict':
			# test map
			self.assertEqual(len(mapped_dict), 2)
			self.assertIsInstance(mapped_dict, dict)
			self.assertEqual(mapped_dict['firstname-cool'], 'John')
			self.assertEqual(mapped_dict['active-cool'], True)
		return mapped_dict

	def test_JSON_model_format(self):

		''' Try serializing a Model into a JSON struct. '''

		# sample person
		p = Person(firstname='John', lastname='Doe')

		# prepare mini testsuite
		def test_json_flow(original, js=None):

			if not js:
				# execute for the caller
				original, js = original('to_dict'), original('to_json')

			# test string
			self.assertTrue(len(js) > 0)
			self.assertIsInstance(js, basestring)

			# test decode
			decoded = json.loads(js)
			self.assertIsInstance(decoded, dict)
			self.assertEqual(len(original), len(decoded))

			# test property values
			for key in original:
				self.assertEqual(original[key], decoded[key])

		# test regular to_json
		test_json_flow(p.to_dict(), p.to_json())

		# test all to_dict permutations with json
		test_structs = {
			'raw_dict': self.test_model_to_dict,
			'all_dict': self.test_model_to_dict_all_arguments,
			'mapped_dict': self.test_model_to_dict_with_map,
			'filtered_dict': self.test_model_to_dict_with_filter,
			'included_dict': self.test_model_to_dict_with_include,
			'excluded_dict': self.test_model_to_dict_with_exclude
		}

		# test each dict => json flow
		test_json_flow(test_structs['raw_dict'])
		test_json_flow(test_structs['all_dict'])
		test_json_flow(test_structs['mapped_dict'])
		test_json_flow(test_structs['filtered_dict'])
		test_json_flow(test_structs['included_dict'])
		test_json_flow(test_structs['excluded_dict'])

	def test_explicit(self):

		''' Test a Model's behavior in `explicit` mode. '''

		# sample people
		s = Person(firstname='Sam')
		p = Person(firstname='John')

		# go into explicit mode
		self.assertEqual(p.__explicit__, False)
		explicit_firstname, explicit_lastname, explicit_active = None, None, None
		with p:
			explicit_firstname, explicit_lastname, explicit_active = p.firstname, p.lastname, p.active
			self.assertNotEqual(p.__explicit__, s.__explicit__)  # only instances switch modes

			self.assertEqual(s.lastname, None)
			self.assertEqual(s.active, True)
			self.assertEqual(s.firstname, 'Sam')
			self.assertEqual(p.__explicit__, True)
		self.assertEqual(p.__explicit__, False)

		# test explicit values
		self.assertEqual(explicit_firstname, 'John')
		self.assertEqual(explicit_active, datastructures._EMPTY)  # default values are not returned in `explicit` mode
		self.assertEqual(explicit_lastname, datastructures._EMPTY)  # unset properties are returned as _EMPTY in `explicit` mode

		# test implicit values
		self.assertEqual(p.firstname, 'John')
		self.assertEqual(p.lastname, None)
		self.assertEqual(p.active, True)

	def test_generator_implicit(self):

		''' Test a Model's behavior when used as an iterator. '''

		# sample person
		p = Person(firstname='John')

		# test implicit generator
		items = {}
		for name, value in p:
			items[name] = value

		self.assertEqual(len(items), 2)  # `active` should show up with default
		self.assertEqual(items['firstname'], 'John')
		self.assertEqual(items['active'], True)

	def test_generator_explicit(self):

		''' Test a Model's behavior when used as an iterator in `explicit` mode. '''

		# sample person
		p = Person(firstname='John')

		# test explicit generator
		items = {}
		with p:
			for name, value in p:
				items[name] = value

		self.assertEqual(len(items), len(p.__lookup__))  # should have _all_ properties
		self.assertEqual(items['firstname'], 'John')
		self.assertEqual(items['active'], datastructures._EMPTY)  # defaults are returned as sentinels in `explicit` mode
		self.assertEqual(items['lastname'], datastructures._EMPTY)  # unset properties are returned as sentinels in `explicit` mode

	def test_len(self):

		''' Test a Model's behavior when used with `len()`. '''

		# sample person
		p = Person()
		self.assertEqual(len(p), 0)

		# set 1st property
		p.firstname = 'John'
		self.assertEqual(len(p), 1)

		# set 2nd property
		p.lastname = 'Doe'
		self.assertEqual(len(p), 2)

	def test_nonzero(self):

		''' Test a Model's falsyness with no properties. '''

		# sample peron
		p = Person()
		self.assertTrue((not p))  # empty model should be falsy

		p.firstname = 'John'
		self.assertTrue(p)  # non-empty model is not falsy

	def test_parent(self):

		''' Test ancestor functionality with a parented Model. '''

		pass  # @TODO: test parented models

	def test_raw(self):

		''' Try serializing a Model into and out of its raw form. '''

		pass  # @TODO: raw entity format