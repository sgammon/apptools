## Base Imports
import abc


## Model layer exceptions
class DatamodelError(Exception): ''' Abstract base exception for model errors. '''
class KeyError(DatamodelError): ''' Parent for all key-related errors. '''
class EmptyKey(KeyError): ''' Thrown when an incomplete key is operated on. '''


## ThinKeyAdapter - adapts model keys to a given storage backend
class ThinKeyAdapter(object):

    ''' Represents a ThinModel's unique DB key. '''

    # Private Members
    __id__ = None
    __app__ = None
    __kind__ = None
    __value__ = None
    __parent__ = None
    __adapter__ = None
    __namespace__ = None
    __persisted__ = False

    __metaclass__ = abc.ABCMeta

    ## == External Key Methods == ##
    def __init__(self, namespace, kind, parent=None, id=None, adapter=None, raw=None, app=None):

        ''' Init a new key, usually from cls.__inflate__. '''

        # if we're inflating, it's an existing key
        if raw:
            self.__persisted__ = True

        self.__app__, self.__adapter__, self.__value__ = app, adapter, raw
        self.__namespace__, self.__parent__, self.__kind__, self.__id__ = namespace, parent, kind, id

    def get(self, **opts):

        ''' Retrieve an entity from the datastore, by key. '''

        if self.__value__ is None:
            raise EmptyKey("Must fully construct a key before attempting to get().")

        return self.__adapter__.get(self)

    def delete(self):

        ''' Delete an entity from the datastore, by key. '''

        if self.__value__ is None:
            raise EmptyKey("Must fully construct a key before attempting to delete().")

        return self.__adapter__.delete(self)

    ## == Internal Key Methods == ##
    def id(self):

        ''' Return this key's ID, whether string or string-based. '''

        return self.__id__

    def kind(self):

        ''' Return the kind name of this key. '''

        return self.__kind__

    def parent(self):

        ''' Return the parent key to this key. '''

        return self.__parent__

    def pairs(self):

        ''' Return the raw pairs describing this key. '''

        return [(self.__kind__, self.__id__)]

    def app(self):

        ''' Return the application that created this key. Not used in an 'AppFactory' env. '''

        return self.__app__

    def urlsafe(self):

        ''' Produce a stringified representation of the key, suitable for use in a URL. '''

        raise NotImplemented

    def flat(self):

        ''' Produce a flattened version of this key. '''

        raise NotImplemented

    ## == AppTools Hooks == ##
    @abc.abstractmethod
    def __inflate__(self, struct): ''' Construct a new key from a string. '''

    def __encode__(self): ''' Output an encoded representation of this key. '''
    def __message__(self, exclude=None, include=None): ''' Output a struct representing this key that is suitable for transmission. '''


## ThinModelAdapter - adapts thinmodels to a given storage backend
class ThinModelAdapter(object):

    ''' Adapts apptools ThinModels to a given storage backend. '''

    __metaclass__ = abc.ABCMeta

    __key__ = None
    __dirty__ = False
    __persisted__ = False

    ## == Internal Methods == ##
    def __adapter(self, opts):

        ''' Resolve an adapter, if specified. '''

        # operation-level explicit adapter
        if 'adapter' in opts:
            adapter = opts.get('adapter').lower()
            if adapter in self.__adapt__:
                return self.__adapt__[adapter]
            else:
                raise AdapterNotFound("Could not resolve adapter at name '%s'." % adapter)

        # model-level explicit adapter
        elif hasattr(self, '_adapter'):
            if isinstance(self._adapter, basestring):
                if self._adapter in self.__adapt__:
                    return self.__adapt__[self._adapter]
                else:
                    raise AdapterNotFound("Could not resolve adapter at name '%s'." % self._adapter)

        # use default adapter
        else:
            return self.__adapt__[self.__default__]

    ## == Datastore Methods == ##
    def get(self, *args, **opts):

        ''' Retrieve an entity from storage. '''

        return self.__adapter(opts).get(*args, **opts)

    def put(self, *args, **opts):

        ''' Store/save an entity in storage. '''

        return self.__adapter(opts).put(self, *args, **opts)

    def delete(self, *args, **opts):

        ''' Delete a model from storage. '''

        return self.__adapter(opts).delete(self.key, *args, **opts)

    def query(self, *args, **opts):

        ''' Start a query from this ThinModel. '''

        return self.__adapter(opts).query(*args, **opts)

    ## == Special Properties == ##
    @property
    def key(self):

        ''' Retrieve this entity's key. '''

        return self.__key__

    ## == Special Methods == ##
    def to_dict(self, exclude=None, include=None):

        ''' Export a dictionary representation of this ThinModel to a dictionary. '''

        if exclude:
            property_set = [p for p in self.__lookup__ if p not in exclude]
        elif include and not exclude:
            property_set = [p for p in self.__lookup__ if p in include]
        else:
            property_set = self.__lookup__

        m_dict = {}
        for k in property_set:
            m_dict[k] = getattr(self, k)
        return m_dict

    @abc.abstractmethod
    def __json__(self): ''' Output a JSON-encoded representation of this model. '''

    @abc.abstractmethod
    def __message__(self): ''' Output a structured representation of this model, suitable for transmission. '''

    @abc.abstractmethod
    def __inflate__(self, key, struct): ''' Inflate a raw structure into an adapted model instance. '''


## StorageAdapter - central controller for managing requests to/from storage engines
class StorageAdapter(object):

    ''' Adapts the AppTools core model APIs to a given storage backend. '''

    name = None
    __metaclass__ = abc.ABCMeta
    supported = lambda x: False

    ## == Datastore Methods == ##
    @abc.abstractmethod
    def get(self, key, **opts): ''' Retrieve one or multiple entities by key. '''

    @abc.abstractmethod
    def put(self, entity, **opts): ''' Persist one or multiple entities. '''

    @abc.abstractmethod
    def delete(self, target, **opts): ''' Delete an entity by key or model instance. '''

    @abc.abstractmethod
    def query(self, kind=None, **opts): ''' Start building a query, optionally over `kind`. '''

    ## == Metadata Methods == ##
    @abc.abstractmethod
    def kinds(self, **opts): ''' Retrieve a list of active kinds in this storage backend. '''

    def __hash__(self):

        ''' Return a hash for this storage engine, enabling this object to be stored as a dict key or tuple member. '''

        return self.__class__.__name__
