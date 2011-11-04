# -*- coding: utf-8 -*-

# NDB Imports
from ndb import key
from ndb import model

from apptools.util import DictProxy

# App Engine Imports
from google.appengine.ext import db as ldb
from google.appengine.ext import blobstore

from google.appengine.api import datastore_types
from google.appengine.api import datastore_errors

# Internal settings
_LOG_IMPORTS = True
_PATH_SEPERATOR = ':'
_KEY_NAME_SEPERATOR = '//'

_PATH_KEY_PROPERTY	= '_path_'
_CLASS_KEY_PROPERTY = '_class_'

_class_map = {}


## Property Classes

# NDB/New Style
ndb = DictProxy({
		'StringProperty' : model.StringProperty,
		'TextProperty' : model.TextProperty,
		'BlobProperty' : model.BlobProperty,
		'IntegerProperty' : model.IntegerProperty,
		'FloatProperty' : model.FloatProperty,
		'BooleanProperty': model.BooleanProperty,
		'DateTimeProperty': model.DateTimeProperty,
		'TimeProperty': model.TimeProperty,
		'GeoPtProperty': model.GeoPtProperty,
		'KeyProperty' : model.KeyProperty,
		'UserProperty': model.UserProperty,
		'StructuredProperty' : model.StructuredProperty,
		'LocalStructuredProperty' : model.LocalStructuredProperty,
		'ComputedProperty' : model.ComputedProperty,
		'GenericProperty': model.GenericProperty
})

# DB/Old Style
db = DictProxy({
		'StringProperty' : ldb.StringProperty,
		'ByteStringProperty' : ldb.ByteStringProperty,		
		'BooleanProperty' : ldb.BooleanProperty,
		'IntegerProperty' : ldb.IntegerProperty,
		'FloatProperty' : ldb.FloatProperty,
		'DateTimeProperty' : ldb.DateTimeProperty,
		'DateProperty' : ldb.DateProperty,
		'TimeProperty' : ldb.TimeProperty,
		'ListProperty' : ldb.ListProperty,
		'StringListProperty' : ldb.StringListProperty,
		'ReferenceProperty' : ldb.ReferenceProperty,
		'BlobReferenceProperty' : blobstore.BlobReferenceProperty,
		'UserProperty' : ldb.UserProperty,
		'BlobProperty' : ldb.BlobProperty,
		'TextProperty' : ldb.TextProperty,
		'CategoryProperty' : ldb.CategoryProperty,
		'LinkProperty' : ldb.LinkProperty,
		'EmailProperty' : ldb.EmailProperty,
		'GeoPtProperty' : ldb.GeoPtProperty,
		'IMProperty' : ldb.IMProperty,
		'PhoneNumberProperty' : ldb.PhoneNumberProperty,
		'PostalAddressProperty' : ldb.PostalAddressProperty,
		'RatingProperty' : ldb.RatingProperty
})

def property_classes(flatten=False):
	class_lists = [db, ndb]
	p_list = []
	for class_list in class_lists:
		for p_name, p_class in class_list.items():
			if flatten is True: p_list.append(p_name)
			if flatten is False: p_list.append((p_name, p_class))
	return p_list

## _ModelPathProperty
# This property is used in PolyPro to store the model's type inheritance path.
class _ModelPathProperty(ldb.StringProperty):
	
	''' Stores the Python package import path from the application root, for lazy-load on search. '''

	def __init__(self, name, **kwargs):
		super(_ModelPathProperty, self).__init__(name=name, default=None, **kwargs)

	def __set__(self, *args):
		raise ldb.DerivedPropertyError('Model-path is a derived property and cannot be set.')

	def __get__(self, model_instance, model_class):
		if model_instance is None: return self
		return model_instance._getModelPath(':')

## _ClassKeyProperty
# This property is used in PolyPro to store the model's class path.
class _ClassKeyProperty(ldb.ListProperty):
	
	''' Stores the polymodel class inheritance path. '''

	def __init__(self, name):
		super(_ClassKeyProperty, self).__init__(name=name,item_type=str,default=None)

	def __set__(self, *args):
		raise ldb.DerivedPropertyError('Class-key is a derived property and cannot be set.')

	def __get__(self, model_instance, model_class):
		if model_instance is None: return self
		return model_instance._getClassPath()

## BaseModel
# This is the root base model for all AppTools-based models.
class BaseModel(object):

	''' Root, master, non-polymorphic data model. Everything lives under this class. '''

	def _getModelPath(self,seperator=None):

		path = [i for i in str(self.__module__+'.'+self.__class__.__name__).split('.')]

		if seperator is not None:
			return seperator.join(path)

		return path

	def _getClassPath(self, seperator=None):

		if hasattr(self, '__class_hierarchy__'):
			path = [cls.__name__ for cls in self.__class_hierarchy__]

			if seperator is not None:
				return seperator.join(path)
			return path
		else:
			return []