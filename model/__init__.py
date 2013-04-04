# -*- coding: utf-8 -*-

'''

	apptools2: model API
	-------------------------------------------------
	|												|	
	|	`apptools.model`							|
	|												|
	|	a general-purpose, minimalist toolkit for 	|
	|	extensible pythonic data modelling.			|
	|												|	
	-------------------------------------------------
	|	authors:									|
	|		-- sam gammon (sam@momentum.io)			|
	-------------------------------------------------	
	|	changelog:									|
	|		-- apr 1, 2013: initial draft			|
	-------------------------------------------------

'''

# stdlib
import abc
import base64
import weakref
import operator
import collections

# relative imports
from . import adapter
from .adapter import concrete

# apptools util
from apptools import util
from apptools.util import json

# apptools datastructures
from apptools.util.datastructures import _EMPTY


## == protorpc support == ##
try:
	import protorpc
	from protorpc import messages as pmessages
	from protorpc import message_types as pmessage_types

except ImportError as e:
	# flag as unavailable
	_PROTORPC, _root_message_class = False, object

else:
	# flag as available
	_PROTORPC, _root_message_class = True, pmessages.Message


## == appengine support == ##

# try to find appengine pipelines
try:
	import pipeline
	from pipeline import common as _pcommon
	from pipeline import pipeline as _pipeline

except ImportError as e:
	# flag as unavailable
	_PIPELINE, _pipeline_root_class = False, object

else:
	# flag as available
	_PIPELINE, _pipeline_root_class = True, _pipeline.Pipeline

# try to find appengine's NDB
try:
	from google.appengine.ext import ndb as nndb

# if it's not available, redirect key/model parents to native <object>
except ImportError as e:
	_NDB, _key_parent, _model_parent = False, lambda: object, lambda: object

# if it *is* available, we need to inherit from NDB's key and model classes
else:
	_NDB, _key_parent, _model_parent = True, lambda: nndb.Key, lambda: nndb.MetaModel


# Globals / Sentinels
_MULTITENANCY = False  # toggle multitenant key namespaces
_DEFAULT_KEY_SCHEMA = frozenset(['id', 'kind', 'parent', 'app'])  # default schema for key classes


## == Metaclasses == ##

## MetaFactory
# Abstract metaclass parent that provides common construction methods.
class MetaFactory(type):

	''' Abstract parent for model metaclasses. '''

	__metaclass__ = abc.ABCMeta

	## = Internal Methods = ##
	def __new__(cls, name, bases, properties):

		''' Factory for model metaclasses. '''

		# pass up the inheritance chain to `type`, which properly enforces metaclasses
		return super(MetaFactory, cls).__new__(cls, *cls.initialize(name, bases, properties))

	## = Exported Methods = ##
	@classmethod
	def resolve(cls, name, bases, properties):

		''' Resolve a suitable adapter set for a given class. '''

		## @TODO: Implement actual driver/adapter resolution
		if '__adapter__' in properties:
			for available in available_adapters:
				if available is properties.get('__adapter__') or available.__name__ == properties.get('__adapter__'):
					return available.acquire()

		available_adapters = []
		for option in adapter.concrete:
			if option.is_supported():
				available_adapters.append(option)

		# we only have one adapter, the choice is easy
		return available_adapters[0].acquire()

	## = Abstract Methods = ##
	@abc.abstractmethod
	def initialize(cls, name, bases, properties):

		''' Initialize a subclass. Must be overridden by child metaclasses. '''

		raise NotImplemented()


## == Abstract Classes == ##

## AbstractKey
# Metaclass for a datamodel key class.
class AbstractKey(_key_parent()):

	''' Abstract Key class. '''

	__schema__ = _DEFAULT_KEY_SCHEMA if not _MULTITENANCY else frozenset(['id', 'kind', 'parent', 'namespace', 'app'])

	## = Encapsulated Classes = ##

	## AbstractKey.__metaclass__
	# Constructs and prepares Key classes for use in the AppTools model subsystem.
	class __metaclass__(MetaFactory):

		''' Metaclass for model keys. '''

		__schema__ = _DEFAULT_KEY_SCHEMA

		@classmethod
		def initialize(cls, name, bases, properties):

			''' Initialize a Key class. '''

			# build initial key class structure
			key_class = {
				'__slots__': set(),  # seal object attributes, keys don't need any new space
				'__format__': set(),  # store the format for a key at the class level (allows easy de-serialization)
			}

			# provision each key schema point in our format pointer and slots allocation
			for name in properties.get('__schema__', cls.__schema__):
				key_class['__format__'].add(name)  # regular name goes into format (for example, `id`)
				key_class['__slots__'].add('__%s__' % name)  # special name goes into slots (for example, `__id__`)

			if '__adapter__' not in properties:
				key_class['__adapter__'] = cls.resolve(name, bases, properties)

			# return an argset for `type`
			return name, bases, key_class


## AbstractModel
# Metaclass for a datamodel class.
class AbstractModel(_model_parent()):

	''' Abstract Model class. '''

	__slots__ = tuple()

	## = Encapsulated Classes = ##

	## AbstractModel.__metaclass__
	# Initializes class-level property descriptors and re-writes model internals.
	class __metaclass__(MetaFactory):

		''' Metaclass for data models. '''

		@classmethod
		def initialize(cls, name, bases, properties):

			''' Initialize a Model class. '''

			if name not in frozenset(['AbstractModel', 'Model']):

				# parse property spec (`name = <basetype>` or `name = <basetype>, <options>`)
				property_map = {}

				# model properties that start with '_' are ignored
				for prop, spec in filter(lambda x: not x[0].startswith('_'), properties.items()):
					if isinstance(spec, tuple):
						basetype, options = spec
					else:
						basetype, options = spec, {}

					# build a descriptor object and data slot
					property_map[prop] = Property(prop, basetype, **options)

				# build class layout
				modelclass = {

					# initialize core model class attributes.
					'__impl__': {},  # holds cached implementation classes generated from this model
					'__kind__': name,  # kindname defaults to model class name (keep track of it here so we have it if __name__ changes)
					'__bases__': bases,  # stores a model class's bases, so proper MRO can work
					'__lookup__': frozenset(property_map.keys()),  # frozenset of allocated attributes, for quick lookup
					'__adapter__': cls.resolve(name, bases, properties),  # resolves default adapter class for this key/model
					'__slots__': ()  # seal-off object attributes (but allow weakrefs and explicit flag)

				}

				# update at class-level with descriptor map
				modelclass.update(property_map)

				# inject our own property map, pass-through to `type`
				return name, bases, modelclass

			# pass-through to `type`
			return name, bases, properties


	## AbstractModel.PropertyValue
	# Small, ultra-lightweight datastructure responsible for holding a property value bundle for an entity attribute.
	class _PropertyValue(tuple):

		''' Named-tuple class for property value bundles. '''

		__slots__ = tuple()
		__fields__ = ('dirty', 'data')

		def __new__(_cls, data, dirty=False):

			''' Create a new `PropertyValue` instance. '''

			# pass up-the-chain to `tuple`
			return tuple.__new__(_cls, (data, dirty))

		@classmethod
		def _from_iterable(cls, iterable, new=tuple.__new__, len=len):

			''' Make a new `PropertyValue` object from a sequence or iterable. '''

			result = new(cls, iterable)
			if len(result) != 2:
				raise TypeError('`PropertyValue` expected 2 arguments, got %s.' % len(result))
			return result

		def __repr__(self):

			''' Return a nicely-formatted representation string. '''

			return "Value(data=\"%s\", dirty=%s)" % self

		def _as_dict(self):

			''' Return a new OrderedDict which maps field names to their values. '''

			return collections.OrderedDict(zip(self.__fields__, self))

		__dict__ = property(_as_dict)

		def _replace(self, **kwargs):

			''' Re-create this `PropertyValue` with a new value and dirty flag. '''

			result = self._from_iterable(map(kwargs.pop, self.__fields__), self)
			if kwargs:
				raise ValueError("`PropertyValue` got unexpected field names \"%r\"." % kwargs.keys())
			return result

		def __getnewargs__(self):

			''' Return self as a plain tuple. Used by copy/deepcopy/pickle. '''

			return tuple(self)

		data = property(operator.itemgetter(0), doc='Alias for `PropertyValue.data` at index 0.')
		dirty = property(operator.itemgetter(1), doc='Alias for `PropertyValue.dirty` at index 1.')

	# = Internal Methods = #
	def __repr__(self):

		''' Generate a string representation of this Entity. '''

		return "<%s at ID %s>" % (self.__kind__, 'TEST')

	__str__ = __unicode__ = __repr__


## == Concrete Classes == ##

## Key
# Model datastore key concrete class.
class Key(AbstractKey):

	''' Concrete Key class. '''

	__separator__ = u':'

	## = Internal Methods = ##
	def __new__(cls, urlsafe=None, raw=None, json=None, *parts):

		''' Constructs keys from various formats. '''

		# delegate full-key decoding to classmethods
		if raw:
			return cls.from_raw(raw)  # raw, deserialized keys
		elif urlsafe:
			return cls.from_urlsafe(urlsafe)  # URL-encoded keys
		elif json:
			return cls.from_json(json)  # JSON-formatted keys

		# delegate ordinal/positional decoding to parent class
		return cls(*parts)

	## = Internal Methods = ##
	def __init__(self, _persisted=False, *parts):

		''' Initialize this Key. '''

		# if we're handed initial parts, fill them up in order...
		if parts:
			for name, value in zip(self.__schema__, parts):
				setattr(self, '__%s__' % name, value)  # fill each schema item with a value, if available, in order
		self.__persisted__ = _persisted  # if we *know* this is an existing key, this should be `true`

	def __repr__(self):

		''' Generate a string representation of this Key. '''

		return "<%s of kind '%s' at ID '%s'>" % (self.__class__.__name__, self.kind, id(self))

	__str__ = __unicode__ = __repr__

	def _set_id(self, id):

		''' Set the ID of this Key. '''

		if self.__persisted__:  # disallow changing ID after persistence is achieved
			raise AttributeError('Cannot set the ID of an already-persisted key.')
		self.__id__ = id
		return self

	def _set_kind(self, kind):

		''' Set the kind of this Key. '''

		if self.__persisted__:  # disallow changing kind after persistence is achieved
			raise AttributeError('Cannot set the kind of an already-persisted key.')
		self.__kind__ = kind
		return self

	def _set_parent(self, parent):

		''' Set the parent of this Key. '''

		if self.__persisted__:  # disallow changing parent after persistence is achieved
			raise AttributeError('Cannot change the key parent of an already-persisted key.')
		self.__parent__ = parent
		return self

	def _set_namespace(self, namespace):

		''' Set the namespace of this Key, if supported. '''

		if not _MULTITENANCY:  # multitenancy must be allowed to enable namespaces
			raise RuntimeError('Multitenant key namespaces are not supported in this environment.')
		if self.__persisted__:  # disallow changing namespace after persistence is achieved
			raise AttributeError('Cannot change the key namespace of an already-persisted key.')
		self.__namespace__ = namespace
		return self

	## = Bound Properties = ##
	@property
	def id(self):

		''' Retrieve this Key's ID. '''

		return self.__id__

	@property
	def kind(self):

		''' Retrieve this Key's kind. '''

		return self.__kind__

	@property
	def ancestry(self):

		''' Retrieve this Key's ancestry path. '''

		# if we have a parent, yield to that
		if self.__parent__:
			yield self.__parent__.ancestry

		# yield self to signify the end of the chain, and stop iteration
		yield self
		raise StopIteration()

	## = Object Methods = ##
	def get(self):

		''' Retrieve a previously-constructed key from available persistence mechanisms. '''

		return self.__class__.__adapter__.get_key(self)

	def delete(self):

		''' Delete a previously-constructed key from available persistence mechanisms. '''

		return self.__class__.__adapter__.delete_key(self)

	def flatten(self):

		''' Flatten this Key into a basic structure suitable for transport or storage. '''

		return tuple([getattr(self, i) for i in self.__schema__])

	def urlsafe(self):

		''' Generate an encoded version of this Key, suitable for use in URLs. '''

		return base64.b64encode(self.__class__.__separator__.join([self.flatten()]))

	## = Class Methods = ##
	@classmethod
	def from_raw(cls, encoded, _persisted=False):

		''' Inflate a Key from a raw, internal representation. '''

		return cls(*[chunk for chunk in encoded.split(cls.__separator__)], _persisted=_persisted)

	@classmethod
	def from_urlsafe(cls, encoded, _persisted=False):

		''' Inflate a Key from a URL-encoded representation. '''

		return cls.from_raw(base64.b64decode(encoded), _persisted)


## Property
# Data-descriptor property class.
class Property(object):

	''' Concrete Property class. '''

	## = Internals = ##
	_name = None  # owner property name
	_default = None  # default property value (if any)
	_options = None  # extra, implementation-specific options
	_indexed = False  # index this property, to make it queryable?
	_required = False  # except if this property is unset on put
	_repeated = False  # signifies an array of self._basetype(s)
	_sentinel = _EMPTY  # default sentinel for basetypes/values
	_basetype = _sentinel  # base datatype for the current property

	## = Internal Methods = ##
	def __init__(self, name, basetype,
								default=None,
								required=False,
								repeated=False,
								indexed=None,
								**options):

		''' Initialize this Property. '''

		# copy in property name + basetype
		self.name, self.basetype = name, basetype

		# if we're passed any locally-supported options
		if default is not None: self._default = default
		if indexed is not None: self._indexed = indexed
		if required is not False: self._required = required
		if repeated is not False: self._repeated = repeated

		# extra options
		if options: self._options = options

	## = Descriptor Methods = ##
	def __get__(self, instance, owner):

		''' Descriptor attribute access. '''

		# Proxy to internal method.
		return instance._get_value(self.name)

	def __set__(self, instance, value):

		''' Descriptor attribute write. '''

		return instance._set_value(self.name, value)

	def __delete__(self, instance):

		''' Delete the value of this Descriptor. '''

		return instance._set_value(self.name)

	def valid(self, instance):

		''' Validate the value of this property, if any. '''

		# check for subclass-defined validator
		if hasattr(self, 'validate') and self.__class__ != Property:
			return self.validate(instance)
		else:
			value = instance._get_value(self.name)
			return not any([
				((value in (None, Property._sentinel)) and self._required),  # check null-ness for required properties
				((value is not Property._sentinel) and not isinstance(self._basetype, value))  # check isinstance for regular types
			])

	def validate(self, instance):

		''' Child-overridable validate function. '''

		# must be overridden by child classes
		raise NotImplemented()


## Model
# Concrete class for a data model.
class Model(AbstractModel):

	''' Concrete Model class. '''

	__key__ = Key

	## = Internal Methods = ##
	def __init__(self, key=None, _persisted=False, **properties):

		''' Initialize this Model. '''

		# if we're handed a key at construction time, it's manually set...
		if isinstance(key, basestring):
			self._set_key(urlsafe=key)
		elif key:
			self._set_key(constructed=key)
		else:
			self._set_key(self.__key__(self.kind))  # create an empty, kinded key

		# initialize internals and map any kwargs into data
		self._initialize(_persisted)._set_value(properties, _dirty=(not _persisted))

	def __setattr__(self, name, value):

		''' Attribute write override. '''

		if name.startswith('__') or name in self.__lookup__:
			super(Model, self).__setattr__(name, value)
		else:
			raise AttributeError("Cannot set nonexistent attribute \"%s\" of model class \"%s\"." % (name, self.kind))

	def _initialize(self, _persisted):

		''' Initialize core properties. '''

		# initialize core properties
		self.__data__, self.__dirty__, self.__persisted__, self.__explicit__, self.__initialized__ = {}, (not _persisted), _persisted, False, True
		return self

	def _set_key(self, urlsafe=None, constructed=None, raw=None):

		''' Set this Entity's key manually. '''

		if urlsafe:
			self.__key__ = Key.from_urlsafe(urlsafe)
		elif constructed:
			self.__key__ = constructed
		elif raw:
			self.__key__ = Key.from_raw(raw)

	def _get_value(self, name, sentinel=_EMPTY):

		''' Retrieve the value of a named property on this Entity. '''

		if name in self.__lookup__:
			value = self.__data__.get(name, None)

			if value:
				return value.data
			else:
				# return sentinel in explicit mode, if property is unset
				if self.__explicit__ and value is Property._sentinel:
					return Property._sentinel
				else:
					return None

		raise AttributeError("Model \"%s\" has no property \"%s\"." % (self.kind, name))

	def _set_value(self, name, value=_EMPTY, _dirty=True):

		''' Set (or reset) the value of a named property on this Entity. '''

		# empty strings or dicts or iterables return self
		if not name:
			return self

		# allow a list of (name, value) pairs, just delegate to self and recurse
		if isinstance(name, (list, tuple)) and isinstance(name[0], tuple):
			return (self._set_value(i, _dirty=_dirty) for i in name)

		# allow a tuple of (name, value), for use in map/filter/etc
		if isinstance(name, tuple):
			name, value = name

		# check property lookup
		if name in self.__lookup__:
			# if it's a valid property, create a namedtuple value placeholder
			self.__data__[name] = self.__class__._PropertyValue(value, _dirty)

			# set as dirty if this is after first construction
			if not (value == _EMPTY) and not self.__dirty__ and _dirty:
				self.__dirty__ = True
			return self
		raise AttributeError("Model \"%s\" has no property \"%s\"." % (self.kind, name))

	## = Properties = ##
	@property
	def key(self):

		''' Retrieve this Model's Key, if any. '''

		return self.__key__

	## = Class Methods = ##
	@classmethod
	def kind(cls):

		''' Retrieve this Model's kind name. '''

		return cls.__name__

	@classmethod
	def get(cls, key=None, name=None):

		''' Retrieve a persisted version of this model via the current datastore adapter. '''

		if key:
			if isinstance(key, basestring):
				# assume URL-encoded key, this is user-facing
				key = Key.from_urlsafe(key)
			elif isinstance(key, (list, tuple)):
				# an ordered partslist is fine too
				key = Key(*key)
			return cls.__adapter__.get_key(key)
		if name:
			# if we're passed a name, construct a key with the local kind
			return cls.__adapter__.get_key(Key(cls.kind(), name))
		raise ValueError('Must pass either a Key or key name into `%s.get`.' % cls.kind())

	## = Public Methods = ##
	def put(self, adapter=None):

		''' Persist this entity via the current datastore adapter. '''

		if not adapter:
			adapter = self.__class__.__adapter__
		if not self.key:
			self.key = self.__class__.__key__(self.kind)
		return adapter.put_entity(self)

	def update(self, mapping={}, **kwargs):

		''' Update properties on this model via a merged dict of mapping + kwargs. '''

		if kwargs: mapping.update(kwargs)
		map(lambda x: setattr(self, x[0], x[1]), mapping.items())
		return self

	def to_dict(self, exclude=tuple(), include=tuple(), filter_fn=lambda x: True, map_fn=lambda x: x):

		''' Export this Entity as a dictionary, excluding/including/filtering/mapping as we go. '''

		if not include: include = self.__lookup__
		return dict([i for i in map(map_fn, filter(filter_fn, ((name, getattr(self, name)) for name in self.__lookup__ if (name in include and name not in exclude))))])

	def to_json(self, exclude=tuple(), include=tuple(), filter_fn=lambda x: True, map_fn=lambda x: x):

		''' Export this Entity as a JSON string, excluding/including/filtering/mapping as we go. '''

		return json.dumps(self.to_dict(exclude, include, filter_fn, map_fn))


## == Test Models == ##

## Car
# Simple model simulating a car.
class Car(Model):

	''' An automobile. '''

	make = basestring, {'indexed': True}
	model = basestring, {'indexed': True}
	year = int, {'choices': xrange(1900, 2015)}
	color = basestring, {'choices': ('blue', 'green', 'red', 'silver', 'white', 'black')}


## Person
# Simple model simulating a person.
class Person(Model):

	''' A human being. '''

	firstname = basestring
	lastname = basestring
	active = bool, {'default': True}
	cars = Car, {'repeated': True}
