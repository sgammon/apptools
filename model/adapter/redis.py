## Base Imports
import redis

## Model Imports
from apptools.model.adapter import ModelAdapter
from apptools.model.adapter import ModelKeyAdapter


## RedisKey - adapts model keys to redis
class RedisKey(ModelKeyAdapter):

	''' Provides models with keys for use in Redis. '''

	def get(self):

		''' Retrieve an entity from Redis by its key. '''

		pass

	def get_async(self):

		''' Asynchronously retrieve an entity from Redis by its key. '''

		pass

	def delete(self):

		''' Delete an entity in Redis by its key. '''

		pass

	def delete_async(self):

		''' Asynchronously delete an entity from Redis by its key. '''

		pass

	def id(self):

		''' Retrieve this key's string/integer ID. '''

		pass

	def kind(self):

		''' Retrieve this key's kind name. '''

		pass

	def parent(self):

		''' Retrieve this key's parent key. '''

		pass

	def pairs(self):

		''' Retrieve this key's pairs. '''

		pass

	def app(self):

		''' Retrieve the app that created this key. '''

		pass

	def urlsafe(self):

		''' Generate a string representation of this key, suitable for use in a URL. '''

		pass

	def flat(self):

		''' Flatten this key. '''

		pass


## RedisAdapter - class that adapts thinmodels for storage in Redis
class RedisAdapter(ModelAdapter):

	''' Adapts ThinModels to use Redis for storage. '''

	def __json__(self):

		''' Return a JSON representation of this model. '''

		pass

	def __message__(self):

		''' Return a structured representation of this model, suitable for transmission. '''

		pass

        def key(self):
		
		''' Retrieve this entity's key. '''

		pass

        def get(self):

		''' Retrieve an entity from storage. '''

		pass

        def put(self):

		''' Store/save an entity in storage. '''

		pass

        def delete(self):

		''' Delete a model from storage. '''

		pass

        def query(self):

		''' Start a query from this ThinModel. '''

		pass

