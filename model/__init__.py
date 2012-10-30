# -*- coding: utf-8 -*-

'''

AppTools Models

Exports useful utils/classes for data modelling, along with builtin models
and tools for working with polymorphic persistent data.

-sam (<sam@momentum.io>)

'''

## Base Imports
try:
    import cPickle as pickle
except ImportError, e:
    import pickle

import weakref
import inspect
import datetime
import collections

## AppTools Util
from apptools.util import json
from apptools.util import ObjectProxy
from apptools.util import datastructures

## Constants
_MODEL_PROPERTIES = frozenset([
    '_getModelPath',
    '_getClassPath',
    '_use_cache',
    '_use_memcache',
    '_use_datastore',
    '_post_put_hook',
    '_post_delete_hook'
])

__flattened_properties = None
__unflattened_properties = None

## Defaults
_DEFAULT_PROP_OPTS = {}


## _AppToolsModel
# This model class mixes in a few utilities to all submodels.
class _AppToolsModel(object):

    ''' Root, master, polymorphic-capable thin data model. Everything lives under this class. '''

    def _getModelPath(self, seperator=None):

        ''' Retrieve a path for this model's polymorphic class chain. '''

        path = [i for i in str(self.__module__ + '.' + self.__class__.__name__).split('.')]

        if seperator is not None:
            return seperator.join(path)

        return path

    def _getClassPath(self, seperator=None):

        ''' Retrieve an importable path for this model's class. '''

        if hasattr(self, '__class_hierarchy__'):
            path = [cls.__name__ for cls in self.__class_hierarchy__]

            if seperator is not None:
                return seperator.join(path)
            return path
        else:
            return []


## ThinModelFactory
# Metaclass for converting thin model classes to midway objects that can be expressed as models, messages, dictionaries, etc.
class ThinModelFactory(type):

    ''' Root AppTools model metaclass and factory. '''

    def __new__(self, name, bases, properties):

        ''' Create a ThinModel object if supported, otherwise duck out. '''

        if name == 'ThinModel' or name == 'AppModel':  # don't init abstract models
            return type(name, bases, properties)

        # scan for thin mode, enact it if supported
        thinmode = True
        c_special = []
        c_properties = []

        # filter out/scan for properties
        for k, v in properties.items():
            if k.startswith('__'):
                c_special.append((k, v))
                continue

            if _NDB:
                if isinstance(v, nndb.Property):
                    thinmode = False
                    break
            c_properties.append((k, v))

        # if we're not in thinmode, send it over to NDB
        if not thinmode and _NDB:
            return nndb.Model.__metaclass__.__new__(name, bases, properties)

        # otherwise, generate an internal schema and midway object
        else:
            obj = {}
            schema = []

            obj = {
                '__name__': name,
                '__pmap__': [],
                '__bases__': bases,
                '__lookup__': [],
                '__pclass__': [],
                '__ndb__': {},
                '__impl__': [],
                '__internal__': None,
                '__messages__': None
            }

            obj.update(c_special)

            if '__metaclass__' in properties:
                obj['__metaclass__'] = properties.get('__metaclass__')

            if '_message_class' in properties or '_pipeline_class':
                obj['__impl__'] = tuple([i for i in obj['__impl__'] + [properties.get('_message_class', False), properties.get('_pipeline_class', False)]])

            for k, v in c_properties:

                # if we have explicitly set opts, overlay them on the defaults
                if isinstance(v, tuple):
                    propname, proptype, opts = k, v, dict([(k, v) for k, v in _DEFAULT_PROP_OPTS.items()])
                    proptype, l_opts = v
                    opts.update(l_opts)

                # just a type and no explicit options
                elif v in _BASE_TYPES:
                    propname, proptype, opts = k, v, dict([(k, v) for k, v in _DEFAULT_PROP_OPTS.items()])

                elif inspect.isclass(v) or inspect.isfunction(v) or inspect.ismethod(v) or inspect.ismodule(v):

                    # inline bound classes
                    if (inspect.isclass(v) and k == v.__name__) or not (inspect.isclass(v)):
                        obj[k] = v
                        continue

                else:
                    propname, proptype, opts = k, v, dict([(k, v) for k, v in _DEFAULT_PROP_OPTS.items()[:]])

                if propname not in obj['__lookup__']:
                    obj['__lookup__'].append(propname)
                    obj['__pmap__'].append((propname, proptype, opts))
                    obj[propname] = datastructures.PropertyDescriptor(propname, proptype, opts)
                    obj['__pclass__'].append(weakref.ref(obj[propname]))

            # freeze property lookup
            obj['__internal__'] = collections.namedtuple(name, obj['__lookup__'])
            obj['__slots__'] = tuple()

            import pdb; pdb.set_trace()

            return type(name, bases, obj)


## ThinModel
# Base class for flexible, universal, efficient datamodels.
class ThinModel(_AppToolsModel):

    ''' Base model class for all AppTools models. '''

    __metaclass__ = ThinModelFactory

    def __init__(self, **kwargs):

        ''' Copy kwarg properties in. '''

        for k, v in kwargs.items():
            if k in self.__lookup__:
                setattr(self, k, v)
        return

    @classmethod
    def to_ndb_model(cls, exclude=None, include=None, property_set=None):

        ''' Convert this model to an NDB model class. '''

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

        ndb_props = map(lambda g: (g[0], convert_basetype_to_ndb(g[1], g[2])) if 'impl' not in g[2] else (g[0], resolve_proptype(g[1], g[2])), property_set)

        ndb_impl = nndb.Model.__metaclass__(*[
            cls.__name__, tuple([nndb.Model] + [c for c in cls.__bases__]), dict([(k, v) for k, v in ndb_props])])

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

    @classmethod
    def to_message_model(cls, exclude=None, include=None, property_set=None):

        ''' Convert this model to a ProtoRPC message class. '''

        if not _PROTORPC:
            raise RuntimeError("ProtoRPC is not supported in this environment.")
        if exclude:
            property_set = [k for k in cls.__pmap__ if k[0] not in exclude]
        elif include:
            property_set = [k for k in cls.__pmap__ if k[0] in include]
        elif property_set is None:
            property_set = cls.__pmap__[:]
        lookup_s = tuple([k[0] for k in property_set])

        if lookup_s in cls.__messages__:
            return cls.__messages__.get(lookup_s)

        field_props = map(lambda g: (g[0], convert_basetype_to_field(g[1], g[2])) if 'impl' not in g[2] else (g[0], resolve_fieldtype(g[1], g[2])), property_set)

        msg_impl = nndb.Model.__metaclass__(*[
            cls.__name__, tuple([nndb.Model] + [c for c in cls.__bases__]), dict([(k, v) for k, v in field_props])])

        cls.__messages__[lookup_s] = msg_impl
        return msg_impl


    @classmethod
    def get(self, *args, **kwargs):

        ''' Retrieve a ThinModel from the datastore. '''

        return self.to_ndb_model().get(*args, **kwargs)

    def put(self, *args, **kwargs):

        ''' Persist a ThinModel to the datastore. '''

        return self.to_ndb().put(*args, **kwargs)

    def query(self, *args, **kwargs):

        ''' Query across a ThinModel set in the datastore. '''

        return self.to_ndb().query(*args, **kwargs)

try:
    # App Engine Imports
    from google.appengine.ext import db as ldb
    from google.appengine.ext import blobstore

    # NDB Imports (New DataBase)
    from google.appengine.ext import ndb as nndb
    from google.appengine.ext.ndb import key, model

except ImportError:

    _NDB = False
    _GAE = False

    class _ModelPathProperty(str):
        pass

    class _ClassKeyProperty(list):
        pass

    ## AppTools Model
    # This is the root base model for all AppTools-based models.
    class BaseModel(_AppToolsModel):

        ''' This is the root base model for all AppTools-based models. '''

        pass

else:

    _NDB = True

    ## _ModelPathProperty
    # This property is used in PolyPro to store the model's type inheritance path.
    class _ModelPathProperty(ldb.StringProperty):

        ''' Stores the Python package import path from the application root, for lazy-load on search. '''

        def __init__(self, name, **kwargs):
            super(_ModelPathProperty, self).__init__(name=name, default=None, **kwargs)

        def __set__(self, *args):
            raise ldb.DerivedPropertyError('Model-path is a derived property and cannot be set.')

        def __get__(self, model_instance, model_class):
            if model_instance is None:
                return self
            return model_instance._getModelPath(':')


    ## _ClassKeyProperty
    # This property is used in PolyPro to store the model's class path.
    class _ClassKeyProperty(ldb.ListProperty):

        ''' Stores the polymodel class inheritance path. '''

        def __init__(self, name):
            super(_ClassKeyProperty, self).__init__(name=name, item_type=str, default=None)

        def __set__(self, *args):
            raise ldb.DerivedPropertyError('Class-key is a derived property and cannot be set.')

        def __get__(self, model_instance, model_class):
            if model_instance is None:
                return self
            return model_instance._getClassPath()


    ## AppTools Model
    # This is the root base model for all AppTools-based models.
    class BaseModel(ThinModel, ldb.Model):

        ''' This is the root base model for all AppTools-based models. '''

        pass

    ## NDBModel
    # This is the root base model for all NDB-based models.
    class NDBModel(ThinModel, model.Model):

        ''' This is the root base model for all NDB-based models '''

        pass

    ## BaseExpando
    # This is the root base expando for all expando-based models.
    class BaseExpando(ThinModel, ldb.Expando):

        ''' This is the root base model for all AppTools-based expandos. '''

        pass

    ## NDBExpando
    # This is the root base expando for all NDB-based expandos.
    class NDBExpando(ThinModel, model.Expando):

        ''' This is the root base model for all NDB & Expando-based models. '''

        pass

    ## Property, Key & Model Classes

    # NDB/New Style
    ndb = ObjectProxy({

            'key': key.Key,
            'model': ThinModel,
            'Property': nndb.Property,
            'StringProperty': nndb.StringProperty,
            'TextProperty': nndb.TextProperty,
            'BlobProperty': nndb.BlobProperty,
            'IntegerProperty': nndb.IntegerProperty,
            'FloatProperty': nndb.FloatProperty,
            'BooleanProperty': nndb.BooleanProperty,
            'BlobKeyProperty': nndb.BlobKeyProperty,
            'DateTimeProperty': nndb.DateTimeProperty,
            'TimeProperty': nndb.TimeProperty,
            'GeoPt': nndb.GeoPt,
            'GeoPtProperty': nndb.GeoPtProperty,
            'KeyProperty': nndb.KeyProperty,
            'UserProperty': nndb.UserProperty,
            'JsonProperty': nndb.JsonProperty,
            'PickleProperty': nndb.PickleProperty,
            'StructuredProperty': nndb.StructuredProperty,
            'LocalStructuredProperty': nndb.LocalStructuredProperty,
            'ComputedProperty': nndb.ComputedProperty,
            'GenericProperty': nndb.GenericProperty

    }, case_sensitive=False)

    # DB/Old Style
    db = ObjectProxy({

            'key': ldb.Key,
            'model': BaseModel,
            'StringProperty': ldb.StringProperty,
            'ByteStringProperty': ldb.ByteStringProperty,
            'BooleanProperty': ldb.BooleanProperty,
            'IntegerProperty': ldb.IntegerProperty,
            'FloatProperty': ldb.FloatProperty,
            'DateTimeProperty': ldb.DateTimeProperty,
            'DateProperty': ldb.DateProperty,
            'TimeProperty': ldb.TimeProperty,
            'ListProperty': ldb.ListProperty,
            'StringListProperty': ldb.StringListProperty,
            'ReferenceProperty': ldb.ReferenceProperty,
            'BlobReferenceProperty': blobstore.BlobReferenceProperty,
            'UserProperty': ldb.UserProperty,
            'BlobProperty': ldb.BlobProperty,
            'TextProperty': ldb.TextProperty,
            'CategoryProperty': ldb.CategoryProperty,
            'LinkProperty': ldb.LinkProperty,
            'EmailProperty': ldb.EmailProperty,
            'GeoPtProperty': ldb.GeoPtProperty,
            'IMProperty': ldb.IMProperty,
            'PhoneNumberProperty': ldb.PhoneNumberProperty,
            'PostalAddressProperty': ldb.PostalAddressProperty,
            'RatingProperty': ldb.RatingProperty

    }, case_sensitive=False)


    try:
        from apptools import services
        from protorpc import messages as pmessages

        _PROTORPC = True

        # Message Field Mappings
        _MESSAGE_FIELD_TO_BASETYPE = frozenset([

            ((basestring, str, unicode, model.StringProperty), pmessages.StringField),
            ((int, model.IntegerProperty), pmessages.IntegerField),
            ((float, model.FloatProperty), pmessages.FloatField),
            ((bool, model.BooleanProperty), pmessages.BooleanField),
            ((bytearray, model.ByteStringProperty), pmessages.BytesField),
            ((datetime.datetime, model.DateTimeProperty), pmessages.StringField, lambda x: x.isoformat()),
            ((datetime.date, model.DateProperty), pmessages.StringField, lambda x: x.isoformat()),
            ((datetime.time, model.TimeProperty), pmessages.StringField, lambda x: x.isoformat()),
            ((model.GeoPt, model.GeoPtProperty), pmessages.StringField, lambda x: str(x)),
            ((key.Key, model.KeyProperty), pmessages.StringField, lambda x: x.urlsafe()),
            ((blobstore.BlobKey, model.BlobKeyProperty), pmessages.StringField, lambda x: x.urlsafe()),
            (model.UserProperty, pmessages.StringField, lambda x: x.email()),
            ((ThinModel, model.StructuredProperty, model.LocalStructuredProperty), pmessages.MessageField, lambda x: x.to_message()),
            ((object, dict, model.JsonProperty), pmessages.StringField, json.dumps),
            ((object, dict, model.PickleProperty), pmessages.StringField, pickle.dumps),
            ((None, model.GenericProperty, model.ComputedProperty), services.VariantField)

        ])


        def get_fields():

            ''' Build a set of all available ProtoRPC message fields. '''

            names_to_classes, lookup = {}, set([])
            for bundle in _MESSAGE_FIELD_TO_BASETYPE:
                if len(bundle) == 2:
                    basetypes, field = bundle
                elif len(bundle) == 3:
                    basetypes, field, converter = bundle
                names_to_classes[field.__name__] = field
                lookup.add(field.__name__)
            return names_to_classes, lookup

        _MESSAGE_FIELDS, _MESSAGE_FIELD_LOOKUP = get_fields()


        def resolve_fieldtype(name, options, fail=False):

            ''' Resolve a field type by name, usually from an `impl` property. '''

            if 'impl' in options:
                # resolve by an explicity-declared NDB implementation property
                proptype = resolve_proptype(name, options, True)
                if proptype is not False:
                    return proptype

            if 'field' in options:
                # resolve by an explicitly-declared ProtoRPC message field
                if options['field'] in _MESSAGE_FIELD_LOOKUP:
                    return _MESSAGE_FIELDS.get(options['field'])

            if not fail:
                return services.VariantField
            else:
                return False


        def convert_basetype_to_field(basetype, options, fail=False):

            ''' Convert a basetype to a suitable ProtoRPC message field. '''


            candidate_f = []
            for basegroup in _MESSAGE_FIELD_TO_BASETYPE:
                if basegroup is None:
                    continue  # this field has no basetype conversion path

                if len(basegroup) == 2:
                    basetypes, field = basegroup

                elif len(basegroup) == 3:
                    basetypes, field, converter = basegroup

                if not isinstance(basetypes, tuple):
                    basetypes = (basetypes,)
                if basetype in basetypes:
                    candidate_f.append(field)

            # if we have no candidates
            if not candidate_f and candidate_f == []:
                if not fail:
                    return services.VariantField
                else:
                    return False  # :( indicate we couldn't resolve the message field

            # if we only have one candidate
            elif len(candidate_f) == 1:
                return candidate_f[0]

            # if there are many candidates
            else:
                # return the first, the specification order goes compatible => restrictive
                return candidate_f[0][1]


    except ImportError, e:

        # Empty out our globals and indicate ProtoRPC isn't supported in the current environment.
        _PROTORPC, _MESSAGE_FIELDS, _MESSAGE_FIELD_LOOKUP, _MESSAGE_FIELD_TO_BASETYPE = False, frozenset([]), frozenset([]), frozenset([])


    _MODEL_PROP_TO_BASETYPE = frozenset([

        ((basestring, str, unicode), (model.StringProperty, model.TextProperty), lambda x: model.StringProperty if len(x) < 500 else ndb.TextProperty),
        (int, model.IntegerProperty),
        (float, model.FloatProperty),
        (bool, model.BooleanProperty),
        (bytearray, model.BlobProperty),
        (datetime.datetime, model.DateTimeProperty),
        (datetime.date, model.DateProperty),
        (datetime.time, model.TimeProperty),
        (model.GeoPt, model.GeoPtProperty),
        (key.Key, model.KeyProperty),
        (blobstore.BlobKey, model.BlobKeyProperty),
        (None, model.UserProperty),
        (ThinModel, model.StructuredProperty),
        (ThinModel, model.LocalStructuredProperty),
        (object, model.JsonProperty, json.loads),
        (object, model.PickleProperty, pickle.loads),
        (None, model.GenericProperty, None),
        (None, model.ComputedProperty, None)

    ])


    def get_basetypes():

        ''' Flatten the _MODEL_PROP_TO_BASETYPE structure into a hashable list of basetypes. '''

        # calculate basetype
        _t = [t for t in
                filter(lambda x: x not in frozenset([None, object]),
                    [t[0] for t in _MODEL_PROP_TO_BASETYPE])]

        # expand tuples
        for i, t in enumerate(_t):
            if isinstance(t, tuple):
                for v in t[1:]:
                    _t.append(v)
                _t[i] = t[0]

        return frozenset(_t)

    _BASE_TYPES = get_basetypes()


    def property_classes(flatten=False):

        ''' Return a mapping of all property classes, optionally flattened into a single list. '''

        global __flattened_properties
        global __unflattened_properties

        if flatten is False:
            if __unflattened_properties is not None:
                return __unflattened_properties
        else:
            if __flattened_properties is not None:
                return __flattened_properties

        class_lists = [db, ndb]
        p_list = []
        for class_list in class_lists:
            for p_name, p_class in class_list.items():
                if flatten is True:
                    p_list.append(p_name)
                if flatten is False:
                    p_list.append((p_name, p_class))

        if flatten: __flattened_properties = p_list
        else: __unflattened_properties = p_list

        return p_list


    def resolve_proptype(name, options, fail=False):

        ''' Resolve a property type by name, usually from an `impl` option. '''

        if 'impl' in options:
            basetype, name = name, options.get('impl')
            del options['impl']
        else:
            basetype = name
        if name in ndb:
            return getattr(nndb, name)(**options)
        elif name in db:
            return getattr(ldb, name)(**options)
        else:
            if fail is False:
                return nndb.GenericProperty(**options)
            else:
                return False


    def convert_basetype_to_ndb(basetype, options, fail=False):

        ''' Convert a basetype to an NDB property. '''

        candidate_p = []
        for basegroup in _MODEL_PROP_TO_BASETYPE:
            if basegroup is None:
                continue  # this prop has no basetype conversion path

            if not isinstance(basegroup, tuple):
                basegroup = (basegroup,)
            else:
                if basegroup[0] == None:
                    continue # this prop has no basetype conversion path

                if len(basegroup) == 2:
                    basetypes, proptypes = basegroup
                else:
                    basetypes, proptypes, converter = basegroup

            if not isinstance(basetypes, tuple):
                basetypes = (basetypes,)
            if basetype in basetypes:
                candidate_p.append(proptypes)

        # if we have no candidates
        if not candidate_p and candidate_p == []:
            if not fail:
                return nndb.GenericProperty(**options)
            else:
                return False  # :( indicate we couldn't resolve the property type

        # if we only have one candidate
        elif len(candidate_p) == 1:
            if isinstance(candidate_p[0], tuple):
                if len(candidate_p[0]) == 3:
                    # if there's a converter, use it
                    return candidate_p[0][2](**options)
                else:
                    # have to default to the first (most compatible)
                    return candidate_p[0][0](**options)
            else:
                # there's only one candidate proptype
                return candidate_p[0](**options)
        else:
            return candidate_p[0][0](**options)
