# -*- coding: utf-8 -*-

'''

	apptools2: abstract model adapters
	-------------------------------------------------
	|												|	
	|	`apptools.model.adapter.abstract`			|
	|												|
	|	specifies interface classes that plug-in 	|
	|	to models to allow agnostic storage.		|
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


## ModelAdapter
# Adapt apptools models to a storage backend.
class ModelAdapter(object):

	''' Abstract base class for classes that adapt apptools models to a particular storage backend. '''

	__metaclass__ = abc.ABCMeta

	@classmethod
	def acquire(cls):

		''' Acquire a new copy of this adapter. '''

		return cls()

	@abc.abstractmethod
	def get_key(cls, key):

		''' Retrieve an entity by Key. '''

		raise NotImplemented()

	@abc.abstractmethod
	def delete_key(cls, key):

		''' Delete an entity by Key. '''

		raise NotImplemented()

	@abc.abstractmethod
	def encode_key(cls, key):

		''' Encode a Key for storage. '''

		raise NotImplemented()

	@abc.abstractmethod
	def put_entity(cls, entity):

		''' Persist an Entity in storage. '''

		raise NotImplemented()

	@abc.abstractmethod
	def allocate_ids(cls, kind, count=0):

		''' Allocate new Key IDs for `kind` up to `count`. '''

		raise NotImplemented()


## IndexedModelAdapter
# Adapt apptools models to a storage backend that supports indexing.
class IndexedModelAdapter(ModelAdapter):

	''' Abstract base class for model adapters that support additional indexing APIs. '''

	@abc.abstractmethod
	def generate_indexes(cls, properties):

		''' Generate index entries from a set of indexed properties. '''

		raise NotImplemented()

	@abc.abstractmethod
	def write_indexes(cls, indexes):

		''' Write a batch of index updates generated earlier via the method above. '''

		raise NotImplemented()

	@abc.abstractmethod
	def execute_query(cls, spec):

		''' Execute a query across one (or multiple) indexed properties. '''

		raise NotImplemented()
