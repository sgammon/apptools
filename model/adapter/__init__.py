## Base Imports
import abc


## ModelKey - adapts model keys to a given storage backend
class ModelKeyAdapter(object):

	''' Represents a ThinModel's unique DB key. '''

	__metaclass__ = abd.ABCMeta

	## == External Key Methods == ##
        @abc.abstractmethod
        def get(self): ''' Retrieve an entity from the datastore, by key. '''

        @abc.abstractmethod
        def get_async(self): ''' Asynchronously retrieve an entity from the datastore, by key. '''

        @abc.abstractmethod
        def delete(self): ''' Delete an entity from the datastore, by key. '''

        @abc.abstractmethod
        def delete_async(self): ''' Delete an entity from the datastore, asynchronously, by key. '''

	## == Internal Key Methods == ##
        @abc.abstractmethod
        def id(self): ''' Return this key's ID, whether string or string-based. '''

	@abc.abstractmethod
	def kind(self): ''' Return the kind name of this key. '''

	@abc.abstractmethod
	def parent(self): ''' Return the parent key to this key. '''

	@abc.abstractmethod
	def pairs(self): ''' Return the raw pairs describing this key. '''

	@abc.abstractmethod
	def app(self): ''' Return the application that created this key. Not used in an 'AppFactory' env. '''

	@abc.abstractmethod
	def urlsafe(self): ''' Produce a stringified representation of the key, suitable for use in a URL. '''

	@abc.abstractmethod
	def flat(self): ''' Produce a flattened version of this key. '''


## ModelAdapter - adapts thinmodels to a given storage backend
class ModelAdapter(object):

	''' Adapts apptools ThinModels to a given storage backend. '''

	__metaclass__ = abc.ABCMeta

	## == Special Properties == ##
	@abc.abstractproperty
	def key(self): ''' Retrieve this entity's key. '''

	## == Datastore Methods == ##
	@abc.abstractmethod
	def get(self): ''' Retrieve an entity from storage. '''
	
	@abc.abstractmethod
	def put(self): ''' Store/save an entity in storage. '''

	@abc.abstractmethod
	def delete(self): ''' Delete a model from storage. '''

	@abc.abstractmethod
	def query(self): ''' Start a query from this ThinModel. '''

	## == Special Methods == ##
	@abc.abstractmethod
	def __json__(self): ''' Output a JSON-encoded representation of this model. '''

	@abc.abstractmethod
	def __message__(self): ''' Output a structured representation of this model, suitable for transmission. '''

