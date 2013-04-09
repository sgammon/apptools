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

# app config
try:
	import config
except ImportError as e:  # pragma: no cover
	_APPCONFIG = False
else:
	_APPCONFIG = True

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

except ImportError as e:  # pragma: no cover
	# flag as unavailable
	_PROTORPC, _root_message_class = False, object

else:
	# flag as available
	_PROTORPC, _root_message_class = True, pmessages.Message


## == appengine support == ##

# try to find appengine pipelines
try:  # pragma: no cover
	import pipeline
	from pipeline import common as _pcommon
	from pipeline import pipeline as _pipeline

except ImportError as e:
	# flag as unavailable
	_PIPELINE, _pipeline_root_class = False, object

else:  # pragma: no cover
	# flag as available
	_PIPELINE, _pipeline_root_class = True, _pipeline.Pipeline

# try to find appengine's NDB
try:
	from google.appengine.ext import ndb as nndb

# if it's not available, redirect key/model parents to native <object>
except ImportError as e:  # pragma: no cover
	_NDB, _key_parent, _model_parent = False, lambda: object, lambda: object

# if it *is* available, we need to inherit from NDB's key and model classes
else:  # pragma: no cover
	_NDB, _key_parent, _model_parent = True, lambda: nndb.Key, lambda: nndb.MetaModel


# Globals / Sentinels
_MULTITENANCY = False  # toggle multitenant key namespaces
_DEFAULT_KEY_SCHEMA = tuple(['id', 'kind', 'parent'])  # default schema for key classes


## == Metaclasses == ##

## MetaFactory
# Abstract metaclass parent that provides common construction methods.
class MetaFactory(type):

	''' Abstract parent for model metaclasses. '''

	class __metaclass__(abc.ABCMeta):

		''' Local metaclass for enforcing ABC compliance and __class__.__name__ formatting. '''

		__owner__ = 'MetaFactory'

		def __new__(cls, name=None, bases=tuple(), properties={}):

			''' Factory for metaclasses classes. '''

			if name == '__metaclass__' and hasattr(cls, '__owner__'):
				name = cls.__name__ = cls.__owner__
			return super(cls, cls).__new__(cls, name, bases, properties)

	## = Internal Methods = ##
	def __new__(cls, name=None, bases=tuple(), properties={}):

		''' Factory for model metaclasses. '''

		# fail on regular class construction
		if not name: raise NotImplementedError('Cannot directly instantiate abstract class `MetaFactory`.')

		# pass up the inheritance chain to `type`, which properly enforces metaclasses
		return super(MetaFactory, cls).__new__(cls, *cls.initialize(name, bases, properties))

	## = Exported Methods = ##
	@classmethod
	def resolve(cls, name, bases, properties, default=True):

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
		if len(available_adapters) > 0:
			if not default:
				return available_adapters[0].acquire(), tuple()
			return available_adapters[0].acquire()
		else:
			raise RuntimeError('No Model adapters currently supported.')

	## = Abstract Methods = ##
	@abc.abstractmethod
	def initialize(cls, name, bases, properties):  # pragma: no cover

		''' Initialize a subclass. Must be overridden by child metaclasses. '''

		raise NotImplementedError()  


## == Abstract Classes == ##

## AbstractKey
# Metaclass for a datamodel key class.
class AbstractKey(_key_parent()):

	''' Abstract Key class. '''


	## = Encapsulated Classes = ##

	## AbstractKey.__metaclass__
	# Constructs and prepares Key classes for use in the AppTools model subsystem.
	class __metaclass__(MetaFactory):

		''' Metaclass for model keys. '''

		__owner__ = 'Key'
		__schema__ = _DEFAULT_KEY_SCHEMA

		@classmethod
		def initialize(cls, name, bases, properties):

			''' Initialize a Key class. '''

			if name != 'AbstractKey':

				# build initial key class structure
				key_class = {
					'__slots__': set(),  # seal object attributes, keys don't need any new space
					'__bases__': bases,  # define bases for class
					'__name__': name,  # set class name internals
					'__persisted__': False  # default to not knowing whether this key is persisted
				}

				if '__adapter__' not in properties:
					key_class['__adapter__'] = cls.resolve(name, bases, properties)

				# add key format items, initted to None
				special_properties = dict([('__%s__' % k, None) for k in properties.get('__schema__', cls.__schema__)])
				key_class.update(special_properties)

				# doing this after adding the resolved adapter allows override via `__adapter__`
				key_class.update(properties)  # merge-in properties

				# return an argset for `type`
				return name, bases, key_class

			return name, bases, properties

	def __new__(cls, *args, **kwargs):

		''' Intercepts construction requests for directly Abstract Key classes. '''

		if cls.__name__ == 'AbstractKey':
			raise TypeError('Cannot directly instantiate abstract class `AbstractKey`.')
		else:
			super(_key_parent(), cls).__new__(*args, **kwargs)


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

		__owner__ = 'Model'

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
					'__name__': name,  # map-in internal class name (should be == to Model kind)
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
	def __new__(cls, *args, **kwargs):

		''' Intercepts construction requests for directly Abstract model classes. '''

		if cls.__name__ == 'AbstractModel':
			raise TypeError('Cannot directly instantiate abstract class `AbstractModel`.')
		else:
			return super(AbstractModel, cls).__new__(cls, *args, **kwargs)

	def __repr__(self):

		''' Generate a string representation of this Entity. '''

		return "<%s at ID %s>" % (self.__kind__, self.key.id if self.key else id(self))

	__str__ = __unicode__ = __repr__


## == Concrete Classes == ##

## Key
# Model datastore key concrete class.
class Key(AbstractKey):

	''' Concrete Key class. '''

	__separator__ = u':'
	__schema__ = _DEFAULT_KEY_SCHEMA if not _MULTITENANCY else tuple(['id', 'kind', 'parent', 'namespace', 'app'])

	## = Internal Methods = ##
	def __new__(cls, *parts, **formats):

		''' Constructs keys from various formats. '''

		# delegate full-key decoding to classmethods
		if formats.get('raw'):
			return cls.from_raw(formats.get('raw'))  # raw, deserialized keys
		elif formats.get('urlsafe'):
			return cls.from_urlsafe(formats.get('urlsafe'))  # URL-encoded keys
		elif formats.get('json'):
			return cls.from_json(formats.get('json'))  # JSON-formatted keys

		# delegate ordinal/positional decoding to parent class
		return super(AbstractKey, cls).__new__(cls, *parts, **formats)

	## = Internal Methods = ##
	def __init__(self, *parts, **kwargs):

		''' Initialize this Key. '''

		if len(parts) == 1:  # special case: it's a kinded, empty key
			self.__kind__ = parts[0]
			return

		elif len(parts) == len(self.__schema__):  # it's a fully-spec'ed key
			for name, value in zip(reversed(self.__schema__), parts): setattr(self, name, value)

		elif len(parts) < len(self.__schema__):  # it's a partially-spec'ed key
			# lop off top-level spec items for the negative diff amount of parts specified
			for name, value in zip([i for i in reversed(self.__schema__)][(len(self.__schema__) - len(parts)):], parts):
				setattr(self, name, value)

		else:
			# for some reason the schema falls short of our parts
			raise TypeError("Key type \"%s\" takes a maximum of %s positional arguments to populate the format \"%s\"." % (self.__class__.__name__, len(self.__schema__), str(self.__schema__)))

		self._set_parent(kwargs.get('parent'))  # kwarg-passed parent
		self.__persisted__ = kwargs.get('_persisted', False)  # if we *know* this is an existing key, this should be `true`

	def __eq__(self, other):

		''' Test whether two keys are functionally identical. '''

		# if schemas or classes don't match, immediate no. otherwise check all set values.
		if not other: return other
		if len(self.__schema__) != len(other.__schema__) or not isinstance(other, self.__class__): return False
		return all([i for i in map(lambda x: hasattr(other, x) and (getattr(other, x) == getattr(self, x)), self.__schema__)])

	def __nonzero__(self):

		''' Test whether a key is nonzero, indicating it does/does not have an ID. '''

		return isinstance(self.__id__, (basestring, str))

	def __repr__(self):

		''' Generate a string representation of this Key. '''

		return "<%s of kind %s at ID %s>" % (self.__class__.__name__, self.kind, id(self) if not self.id else str(self.id))

	__str__ = __unicode__ = __repr__

	## = Property Setters = ##
	def _set_id(self, id):

		''' Set the ID of this Key. '''

		if self.__persisted__:  # disallow changing ID after persistence is achieved
			raise AttributeError('Cannot set the ID of an already-persisted key.')
		self.__id__ = id
		return self

	def _set_app(self, app):

		''' Set the appname of this Key. '''

		if self.__persisted__:  # disallow changing the app after persistence is achieved
			raise AttributeError('Cannot set the app of an already-persisted key.')
		self.__app__ = app
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
		if parent:
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

	## = Property Getters = ##
	def _get_id(self):

		''' Retrieve this Key's ID. '''

		return self.__id__

	def _get_kind(self):

		''' Retrieve this Key's kind. '''

		return self.__kind__

	def _get_app(self):

		''' Retrieve this Key's app. '''

		return self.__app__

	def _get_parent(self):

		''' Retrieve this Key's parent. '''

		return self.__parent__

	def _get_namespace(self):

		''' Retrieve this Key's namespace. '''

		if _MULTITENANCY:
			return self.__namespace__
		return

	def _get_ancestry(self):

		''' Retrieve this Key's ancestry path. '''

		# if we have a parent, yield to that
		if self.__parent__:
			ancestry = (i for i in self.__parent__.ancestry)
			for i in ancestry: yield i

		# yield self to signify the end of the chain, and stop iteration
		yield self
		raise StopIteration()

	## = Property Bindings  = ##
	id = property(_get_id, _set_id)
	app = property(_get_app, _set_app)
	kind = property(_get_kind, _set_kind)
	parent = property(_get_parent, _set_parent)
	ancestry = property(_get_ancestry, None)
	namespace = property(_get_namespace, _set_namespace)

	## = Object Methods = ##
	def get(self):

		''' Retrieve a previously-constructed key from available persistence mechanisms. '''

		return self.__class__.__adapter__.get_key(self)

	def delete(self):

		''' Delete a previously-constructed key from available persistence mechanisms. '''

		return self.__class__.__adapter__.delete_key(self)

	def flatten(self, join=False):

		''' Flatten this Key into a basic structure suitable for transport or storage. '''

		flattened = tuple((i if not isinstance(i, self.__class__) else i.flatten(join)) for i in map(lambda x: getattr(self, x), reversed(self.__schema__)))
		if join:
			return self.__class__.__separator__.join(['' if i is None else i for i in flattened])
		return flattened

	def urlsafe(self):

		''' Generate an encoded version of this Key, suitable for use in URLs. '''

		return base64.b64encode(self.flatten(True))

	## = Class Methods = ##
	@classmethod
	def from_raw(cls, encoded, **kwargs):

		''' Inflate a Key from a raw, internal representation. '''

		# if it's still a string, split by separator (probably coming from a DB driver, `urlsafe` does this for us, for instance)
		if isinstance(encoded, basestring): encoded = encoded.split(cls.__separator__)
		encoded = collections.deque(encoded)

		key, keys = [], []
		if not (len(encoded) > len(cls.__schema__)):
			return cls(*encoded, **kwargs)
		else:  # we're dealing with ancestry here
			last_key = encoded.popleft()
			while len(encoded) > 2:
				# recursively decode, removing chunks as we go. extract argset by argset.
				last_key = cls(*(encoded.popleft() for i in xrange(0, len(cls.__schema__) - 1)), parent=last_key, _persisted=kwargs.get('_persisted', False))
			return cls(*encoded, parent=last_key, _persisted=kwargs.get('_persisted', False))

	@classmethod
	def from_urlsafe(cls, encoded, _persisted=False):

		''' Inflate a Key from a URL-encoded representation. '''

		return cls.from_raw(base64.b64decode(encoded), _persisted=_persisted)


## Property
# Data-descriptor property class.
class Property(object):

	''' Concrete Property class. '''

	## = Internals = ##
	_name = None  # owner property name
	_options = None  # extra, implementation-specific options
	_indexed = False  # index this property, to make it queryable?
	_required = False  # except if this property is unset on put
	_repeated = False  # signifies an array of self._basetype(s)
	_sentinel = _EMPTY  # default sentinel for basetypes/values
	_basetype = _sentinel  # base datatype for the current property

	## Default property value
	_default = _sentinel  # default property value (if any)

	## = Internal Methods = ##
	def __init__(self, name, basetype,
								default=None,
								required=False,
								repeated=False,
								indexed=None,
								**options):

		''' Initialize this Property. '''

		# copy in property name + basetype
		self.name, self._basetype = name, basetype

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

		if instance:  # proxy to internal entity method.

			# grab value, returning special a) property default or b) sentinel if we're in explicit mode and it is unset
			if self._default != Property._sentinel:  # we have a set default
				value = instance._get_value(self.name, default=self._default)
			else:
				value = instance._get_value(self.name, default=Property._sentinel)

			if not value and value == Property._sentinel and instance.__explicit__ == False:
				return None  # soak up sentinels via the descriptor API
			return value

		elif self._default: return self._default  # if we have a default and we're at the class level, who cares just give it up i guess
		return None # otherwise, class-level access is always None

	def __set__(self, instance, value):

		''' Descriptor attribute write. '''

		if instance is not None:
			return instance._set_value(self.name, value)
		else:
			raise AttributeError("Cannot write to model property \"%s\" before instantiation." % self.name)

	def __delete__(self, instance):

		''' Delete the value of this Descriptor. '''

		return instance._set_value(self.name)

	def valid(self, instance, throw=True):

		''' Validate the value of this property, if any. '''

		# check for subclass-defined validator
		if hasattr(self, 'validate') and self.__class__ != Property:
			return self.validate(instance)
		else:
			value = instance._get_value(self.name)

			# check required-ness
			if (value in (None, Property._sentinel)) and self._required:
				if not throw:  # optionally fail quietly
					return False
				raise ValueError("Property \"%s\" of Model class \"%s\" is marked as `required`, but was left unset." % (self.name, instance.kind()))

			# check multi-ness
			if isinstance(value, (list, tuple, set, frozenset, dict)):
				if not self._repeated:
					if not throw:  # optionally fail silently
						return False
					raise ValueError("Property \"%s\" of Model class \"%s\" is not marked as repeated, and cannot accept iterable values." % (self.name, instance.kind()))
			else:
				if self._repeated:
					if not throw:  # optionally fail silently
						return False
					raise ValueError("Property \"%s\" of Model class \"%s\" is marked as iterable, and cannot accept non-iterable values." % (self.name, instance.kind()))
				value = [value]

			for v in value:

				# check basetype
				if v is not Property._sentinel and (self._basetype is not Property._sentinel and isinstance(v, self._basetype)):
					continue  # valid instance of basetype
				else:
					if not throw:  # optionally fail quietly
						return False
					raise ValueError("Property \"%s\" of Model class \"%s\" cannot accept value of type \"%s\" (was expecting type \"%s\")." % (self.name, instance.kind(), type(v).__name__, self._basetype.__name__))

			# validation passed! :)
			return True

	def validate(self, instance):

		''' Child-overridable validate function. '''

		# must be overridden by child classes
		raise NotImplemented()


## Model
# Concrete class for a data model.
class Model(AbstractModel):

	''' Concrete Model class. '''

	__key__ = Key
	__explicit__ = False

	## = Internal Methods = ##
	def __init__(self, **properties):

		''' Initialize this Model. '''

		# grab key / persisted flag, if any
		key, persisted = properties.get('key'), properties.get('_persisted', False)

		# if we're handed a key at construction time, it's manually set...
		if isinstance(key, basestring):
			self._set_key(urlsafe=key)
		elif key:
			self._set_key(constructed=key)
		
		# initialize internals and map any kwargs into data
		self._initialize(persisted)._set_value(properties, _dirty=(not persisted))

	def __setattr__(self, name, value):

		''' Attribute write override. '''

		if name.startswith('__') or name in self.__lookup__:
			super(Model, self).__setattr__(name, value)
		else:
			raise AttributeError("Cannot set nonexistent attribute \"%s\" of model class \"%s\"." % (name, self.kind))

	def __context__(self, _type=None, value=None, traceback=None):

		''' Context enter/ext - apply explicit mode. '''

		self.__explicit__ = (not self.__explicit__)
		return self

	__enter__ = __exit__ = __context__

	def __len__(self):

		''' Return the number of written properties. '''

		return len(self.__data__)

	__nonzero__ = __len__

	def __iter__(self):

		''' Allow models to be used as dict-like generators. '''

		for name in self.__lookup__:
			value = self._get_value(name, default=Property._sentinel)
			if (value == Property._sentinel and (not self.__explicit__)):
				if self.__class__.__dict__[name]._default != Property._sentinel:
					yield name, self.__class__.__dict__[name]._default  # return a property's default in `implicit` mode, if any
				continue  # skip unset properties without a default, except in `explicit` mode
			yield name, value
		raise StopIteration()

	def _initialize(self, _persisted):

		''' Initialize core properties. '''

		# initialize core properties
		self.__data__, self.__dirty__, self.__persisted__, self.__explicit__, self.__initialized__ = {}, (not _persisted), _persisted, False, True
		return self

	def _set_key(self, value=None, urlsafe=None, constructed=None, raw=None):

		''' Set this Entity's key manually. '''

		# unknown value
		if value:
			if isinstance(value, basestring):
				return Key.from_urlsafe(value)
			elif isinstance(value, tuple):
				return Key.from_raw(value)
			elif isinstance(value, self.__key__):
				return Key(constructed=value)

		# URLsafe
		if urlsafe:
			self.__key__ = Key.from_urlsafe(urlsafe)

		# constructed key
		elif constructed:
			self.__key__ = constructed

		# raw key
		elif raw:
			self.__key__ = Key.from_raw(raw)

	def _get_value(self, name, default=None):

		''' Retrieve the value of a named property on this Entity. '''

		# calling with no args gives all values in (name, value) form
		if not name:
			values = []
			for i in self.__lookup__:
				values.append((i, self._get_value(i, default)))
			return values

		if name in self.__lookup__:
			value = self.__data__.get(name, Property._sentinel)

			if value:
				return value.data
			else:
				# return system _EMPTY sentinel in explicit mode, if property is unset
				if self.__explicit__ and value is Property._sentinel:
					return Property._sentinel

				# otherwise return handed default, which is usually None
				else:
					return default
		raise AttributeError("Model \"%s\" has no property \"%s\"." % (self.kind, name))

	def _set_value(self, name, value=_EMPTY, _dirty=True):

		''' Set (or reset) the value of a named property on this Entity. '''

		# empty strings or dicts or iterables return self
		if not name:
			return self

		# allow a dict or list of (name, value) pairs, just delegate to self and recurse
		if isinstance(name, dict):
			name = name.items()
		if isinstance(name, (list, tuple)) and isinstance(name[0], tuple):
			return [self._set_value(k, i, _dirty=_dirty) for k, i in name]

		# allow a tuple of (name, value), for use in map/filter/etc
		if isinstance(name, tuple):
			name, value = name

		# if it's a key, set through _set_key
		if name == 'key':
			self._set_key(value)

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

		# Validate property values
		for name in self.__lookup__:
			self.__class__.__dict__[name].valid(self)

		# Allow adapter override
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

	def to_dict(self, exclude=tuple(), include=tuple(), filter=None, map=None, _all=False, filter_fn=filter, map_fn=map):

		''' Export this Entity as a dictionary, excluding/including/filtering/mapping as we go. '''

		dictionary = {}  # return dictionary
		_default_map = False  # flag for default map lambda, so we can exclude only on custom map
		_default_include = False  # flag for including properties unset and explicitly listed in a custom inclusion list

		if not _all: _all = self.__explicit__  # explicit mode implies returning all properties raw

		if not include:
			include = self.__lookup__  # default include list is model properties
			_default_include = True  # mark flag that we used the default

		if not map:
			map = lambda x: x  # substitute no map with a passthrough
			_default_map = True
		
		if not filter: filter = lambda x: True  # substitute no filter with a passthrough

		# freeze our comparison sets
		exclude, include = frozenset(exclude), frozenset(include)

		for name in self.__lookup__:

			# run map fn over (name, value)
			name, value = map((name, self._get_value(name, default=self.__class__.__dict__[name]._default)))  # pull with property default

			# run filter fn over (name, vlaue)
			filtered = filter((name, value))
			if not filtered: continue

			# filter out via exclude/include
			if name in exclude:
				continue
			if not _default_include:
				if name not in include: continue

			if value is Property._sentinel:  # property is unset
				if not _all and not ((not _default_include) and name in include):  # if it matches an item in a custom include list, and/or we don't want all properties...
					continue  # skip if all properties not requested
				else:
					if not self.__explicit__:  # None == sentinel in implicit mode
						value = None
			dictionary[name] = value		
		return dictionary

	def to_json(self, *args, **kwargs):

		''' Export this Entity as a JSON string, excluding/including/filtering/mapping as we go. '''

		return json.dumps(self.to_dict(*args, **kwargs))
