
from google.appengine.ext import ndb

from apptools import model
from apptools.model.adapter import StorageAdapter
from apptools.model.adapter import ThinKeyAdapter
from apptools.model.adapter import ThinModelAdapter


## SQLKeyAdapter - adapts ThinModel keys to SQL row/table IDs
class SQLKeyAdapter(ThinKeyAdapter):

	''' Adapts NDB keys to ThinModel. '''

	## == AppTools Model Hooks == ##
	@classmethod
	def __inflate__(cls, raw):

		''' Inflate a raw string key into an NDB key. '''

		return ndb.Key(urlsafe=raw)

    def id(self):

        ''' Return this key's ID. '''

        pass

    def kind(self):

        ''' Return this key's kind. '''

        pass

    def parent(self):

        ''' Return this key's parent. '''

        pass

    def pairs(self):

        ''' Return this key's pairs. '''

        pass

    def app(self):

        ''' Retrieve the app that made this key. '''

        pass

    def urlsafe(self):

        ''' Return an encoded representation of this key, suitable for use in a URL. '''

        pass

    def flat(self):

        ''' Return a flattened, compact version of this key. '''

        pass


## SQLModelAdapter - adapts ThinModels to SQL-based datastores
class SQLModelAdapter(ThinModelAdapter):

	''' Adapts ThinModels to AppEngine's NDB. '''

	def __json__(self):

		''' Encode this model as JSON. '''

		return json.dumps(self.to_dict())

	def __message__(self, exclude=None, include=None):

		''' Hook to convert to a message class. '''

		return self.to_message(exclude, include)

	@classmethod
	def __inflate__(cls, key, struct):

		''' Inflate to an NDB model from a raw structure. '''

		k = NDBKeyAdapter.__inflate__(key)
		return cls(key=k, **struct)

    @property
    def key(self):

        ''' Retreive this model's key. '''

        return


## SQL - adapts apptools models to SQL-based storage engines
class SQL(StorageAdapter):

    ''' Adapts the AppTools core model APIs to SQL-based storage engines. '''

    def get(self, key, **opts): ''' Retrieve one or multiple entities by key. '''
    def put(self, entity, **opts): ''' Persist one or multiple entities. '''
    def delete(self, target, **opts): ''' Delete one or multiple entities. '''
    def query(self, kind=None, **opts): ''' Start building a query, optionally over a kind. '''
    def kinds(self, **opts): ''' Retrieve a list of active kinds in SQL. '''
