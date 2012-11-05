
from google.appengine.ext import ndb

from apptools.model import _NDB
from apptools.model.adapter import StorageAdapter
from apptools.model.adapter import ThinKeyAdapter
from apptools.model.adapter import ThinModelAdapter


## NDBKeyAdapter
# Adapts ThinModel keys to NDB keys.
class NDBKeyAdapter(ThinKeyAdapter):

    ''' Adapts NDB keys to ThinModel. '''

    ## == AppTools Model Hooks == ##
    @classmethod
    def __inflate__(cls, raw):

        ''' Inflate a raw string key into an NDB key. '''

        return ndb.Key(urlsafe=raw)


## NDBModelAdapter
# Adapts ThinModels to NDB.
class NDBModelAdapter(ThinModelAdapter):

    ''' Adapts ThinModels to AppEngine's NDB. '''

    def key(self):

        ''' Redirect to local key. '''

        return getattr(super(NDBModelAdapter, self), 'key')

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

    @classmethod
    def to_ndb_model(cls, exclude=None, include=None, property_set=None):

        ''' Convert this model to an NDB model class. '''

        from apptools import model

        if not _NDB:
            raise RuntimeError("NDB is not supported in this environment.")
        if exclude:
            property_set = [k for k in cls.__pmap__ if k[0] not in exclude]
        elif include:
            property_set = [k for k in cls.__pmap__ if k[0] in include]
        elif property_set is None:
            property_set = cls.__pmap__[:]
        lookup_s = tuple([k[0] for k in property_set])

        if lookup_s in cls.__ndb__:
            return cls.__ndb__.get(lookup_s)

        ndb_props = map(lambda g: (g[0], model.convert_basetype_to_ndb(g[1], g[2])) if 'impl' not in g[2] else (g[0], model.resolve_proptype(g[1], g[2])), property_set)

        ndb_impl = ndb.Model.__metaclass__(*[
            cls.__name__, tuple([ndb.Model] + [c for c in cls.__bases__ if not issubclass(c, ThinModelAdapter)]), dict([(k, v) for k, v in ndb_props])])

        cls.__ndb__[lookup_s] = ndb_impl
        return ndb_impl

    def to_ndb(self, exclude=None, include=None):

        ''' Convert this model to an NDB model object. '''

        if not _NDB:
            raise RuntimeError("NDB is not supported in this environment.")
        if exclude:
            property_set = [k for k in cls.__pmap__ if k[0] not in exclude]
        elif include:
            property_set = [k for k in cls.__pmap__ if k[0] in include]
        else:
            property_set = self.__pmap__[:]

        model_class = self.to_ndb_model(None, None, property_set)

        n_props = {}
        for k in property_set:
            prop_value = getattr(self, k[0])

            if prop_value is not None:
                n_props[k[0]] = prop_value

        try:
            m_obj = model_class()
            for k, v in n_props.items():
                setattr(m_obj, k, v)
        except Exception, e:
            raise

        return m_obj


## NDB
# Central controller for NDB interactions.
class NDB(StorageAdapter):

    ''' Controller for adapting models to NDB. '''

    ndb = ndb
    key = NDBKeyAdapter
    model = NDBModelAdapter

    def get(self, key, **opts):

        ''' Retrieve one or multiple entities by key. '''

        if isinstance(key, basestring):
            key = self.key.__inflate__(urlsafe=key)
        return self.model.__inflate__(self.ndb.get(key, **opts))

    def put(self, entity, **opts):

        ''' Persist one or multiple entities. '''

        if isinstance(entity, list):
            return self.ndb.put_multi_async(entity).get_result()
        return entity.to_ndb().put(**opts)

    def delete(self, target, **opts):

        ''' Delete one or multiple entities. '''

        return target.key.delete(**opts)

    def query(self, kind=None, **opts):

        ''' Start building a query, optionally over a kind. '''

        return ndb.Query(kind, **opts)

    def kinds(self, **opts):

        ''' Retrieve a list of active kinds in this storage backend. '''

        raise NotImplemented
