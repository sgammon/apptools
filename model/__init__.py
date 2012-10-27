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

## Google Imports
from google.appengine.ext import ndb as nndb

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
_DEFAULT_PROP_OPTS = {
    
}


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

            if isinstance(v, nndb.Property):
                thinmode = False
                break
            c_properties.append((k, v))

        # if we're not in thinmode, send it over to NDB
        if not thinmode:
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
                '__ndb__': {}
            }

            obj.update(c_special)

            if '__metaclass__' in properties:
                obj['__metaclass__'] = properties.get('__metaclass__')
            
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

                obj['__lookup__'].append(propname)
                obj['__pmap__'].append((propname, proptype, opts))
                obj[propname] = datastructures.PropertyDescriptor(propname, proptype, opts)
                obj['__pclass__'].append(weakref.ref(obj[propname]))

            # freeze property lookup
            obj['__slots__'] = frozenset(obj['__lookup__']+obj.keys())

            return type(name, bases, obj)


## ThinModel
# Base class for flexible, universal, efficient datamodels.
class ThinModel(_AppToolsModel):

    ''' Base model class for all AppTools models. '''

    __metaclass__ = ThinModelFactory

    def __new__(self, *args, **kwargs):

        ''' PDB Stop. '''

        return super(ThinModel, self).__new__(self, *args, **kwargs)

    def __init__(self, *args, **kwargs):

        ''' PDB stop. '''

        return

    @classmethod
    def to_ndb_model(cls, exclude=None, include=None, property_set=None):

        ''' Convert this model to an NDB model class. '''

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

        if exclude:
            property_set = [k for k in cls.__pmap__ if k[0] not in exclude]
        elif include:
            property_set = [k for k in cls.__pmap__ if k[0] in include]
        else:
            property_set = self.__pmap__[:]
        model_class = self.to_ndb_model(None, None, property_set)

        n_props = {}
        for k in property_set:
            n_props[k[0]] = getattr(self, k[0])

        return model_class(**n_props)


try:
	# App Engine Imports
	from google.appengine.ext import db as ldb
	from google.appengine.ext import blobstore
	from google.appengine.ext.ndb import key, model

except ImportError:
	
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
	        'Property': model.Property,
	        'StringProperty': model.StringProperty,
	        'TextProperty': model.TextProperty,
	        'BlobProperty': model.BlobProperty,
	        'IntegerProperty': model.IntegerProperty,
	        'FloatProperty': model.FloatProperty,
	        'BooleanProperty': model.BooleanProperty,
	        'BlobKeyProperty': model.BlobKeyProperty,
	        'DateTimeProperty': model.DateTimeProperty,
	        'TimeProperty': model.TimeProperty,
	        'GeoPt': model.GeoPt,
	        'GeoPtProperty': model.GeoPtProperty,
	        'KeyProperty': model.KeyProperty,
	        'UserProperty': model.UserProperty,
	        'JsonProperty': model.JsonProperty,
	        'PickleProperty': model.PickleProperty,
	        'StructuredProperty': model.StructuredProperty,
	        'LocalStructuredProperty': model.LocalStructuredProperty,
	        'ComputedProperty': model.ComputedProperty,
	        'GenericProperty': model.GenericProperty

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

	_MODEL_PROP_TO_BASETYPE = frozenset([

	    ((basestring, str, unicode), (ndb.StringProperty, ndb.TextProperty), lambda x: ndb.StringProperty if len(x) < 500 else ndb.TextProperty),
	    (int, ndb.IntegerProperty),
	    (float, ndb.FloatProperty),
		(bool, ndb.BooleanProperty),
		(bytearray, ndb.BlobProperty),
		(datetime.datetime, ndb.DateTimeProperty),
		(datetime.date, ndb.DateProperty),
		(datetime.time, ndb.TimeProperty),
		(ndb.GeoPt, ndb.GeoPtProperty),
		(ndb.Key, ndb.KeyProperty),
		(blobstore.BlobKey, ndb.BlobKeyProperty),
		(None, ndb.UserProperty),
		(ThinModel, ndb.StructuredProperty),
		(ThinModel, ndb.LocalStructuredProperty),
		(object, ndb.JsonProperty, json.loads),
		(object, ndb.PickleProperty, pickle.loads),
		(None, ndb.GenericProperty, None),
		(None, ndb.ComputedProperty, None)

	])

	_BASE_TYPES = frozenset([t for t in 
		filter(lambda x: x not in frozenset([None, object]),
			[t[0] for t in _MODEL_PROP_TO_BASETYPE])])


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


	def resolve_proptype(name, options, mode='ndb'):

		''' Resolve a property type by name, usually from an `impl` option. '''

		if 'impl' in options:
			del options['impl']
		if name in property_classes(True):
			if mode == 'ndb':
				return ndb.get(name)(**options)
			else:
				return db.get(name)(**options)
		else:
			return ndb.GenericProperty(**options)


	def convert_basetype_to_ndb(basetype, options):

		''' Convert a basetype to an NDB property. '''

		candidate_p = []
		for basegroup in _MODEL_PROP_TO_BASETYPE:
			if basegroup is None:
				continue  # this prop has no basetype conversion path

			if not isinstance(basegroup, tuple):
				basegroup = (basegroup,)
			else:
				if len(basegroup) == 2:
					basetypes, proptypes = basegroup
				else:
					basetypes, proptypes, converter = basegroup

			if not isinstance(basetypes, tuple):
				basetypes = (basetypes,)
			if basetype in basetypes:
				candidate_p.append(proptypes)

		# if we only have one candidate
		if len(candidate_p) == 1:
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
