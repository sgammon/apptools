# -*- coding: utf-8 -*-

'''

	apptools2: model adapter for thread memory
	-------------------------------------------------
	|												|	
	|	`apptools.model.adapter.inmemory`			|
	|												|
	|	allows apptools models to be stored in 		|
	|	main RAM, as a testing tool.				|
	|												|	
	-------------------------------------------------
	|	authors:									|
	|		-- sam gammon (sam@momentum.io)			|
	-------------------------------------------------	
	|	changelog:									|
	|		-- apr 1, 2013: initial draft			|
	-------------------------------------------------

'''

# adapter API
from .abstract import ModelAdapter


## InMemoryAdapter
# Adapt apptools models to Python RAM.
class InMemoryAdapter(ModelAdapter):

	''' Adapt model classes to RAM. '''

	# key encoding
	_key_encoder = base64.b64encode

	# data compression / encoding
	_data_encoder = json.dumps
	_data_compressor = None

	@classmethod
	def is_supported(cls):

		''' Check whether this adapter is supported in the current environment. '''

		return True

	@classmethod
	def get_key(cls, key):

		''' Retrieve an entity by Key from memory. '''

		import pdb; pdb.set_trace()
		return True

	@classmethod
	def delete_key(cls, key):

		''' Delete an entity by Key from memory. '''

		import pdb; pdb.set_trace()
		return True

	@classmethod
	def encode_key(cls, key):

		''' Encode a Key for storage in memory. '''

		import pdb; pdb.set_trace()
		return True

	@classmethod
	def put_entity(cls, entity):

		''' Persist an entity to storage in memory. '''
		
		import pdb; pdb.set_trace()
		return True

	@classmethod
	def allocate_ids(cls, count=1):

		''' Allocate new Key IDs up to `count`. '''

		pass
