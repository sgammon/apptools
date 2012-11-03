## Base Imports
import redis

## Model Imports
from apptools.model.adapter import ModelAdapter
from apptools.model.adapter import ModelKeyAdapter


## RedisKey - adapts model keys to redis
class RedisKey(ModelKeyAdapter):

	''' Provides models with keys for use in Redis. '''

	## == AppTools Model Hooks == ##
	@classmethod
	def __inflate__(cls, struct):

		''' Inflate a raw structure from Redis into a key. '''

		pass

	def __message__(self, exclude=None, include=None):

		''' Convert this model into a structure suitable for transmission. '''

		pass

	def __json__(self):

		''' Encode a structured representation of this model in JSON. '''

		pass

	## == Datastore Methods == ##
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

	## == Internal Key Methods == ##
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


	## == AppTools Model Hooks == ##
	@classmethod
	def __inflate__(cls, struct):

		''' Inflate a raw Redis structure into a model. '''

		pass

	def __message__(self):

		''' Return a structured representation of this model, suitable for transmission. '''

		pass

	def __json__(self):

		''' Return a JSON representation of this model. '''

		pass

	## == Datastore Methods == ##
    def get(self):

		''' Retrieve an entity from storage. '''

		pass

    def put(self):

		''' Store/save an entity in storage. '''

		pass

    def delete(self):

		''' Delete a model from storage. '''

		pass

	## == Internal Model Methods == ##
	@property
    def key(self):

		''' Retrieve this entity's key. '''

		pass

    def query(self):

		''' Start a query from this ThinModel. '''

		pass

