# -*- coding: utf-8 -*-
import logging

class UtilStruct(object):

	''' Abstract class for a utility object. '''
	
	_type = None
	
	## Init -- Accept structure fill
	def __init__(self, struct=None, **kwargs):
		
		''' If handed a dictionary (or something) in init, send it to fillStructure (and do the same for kwargs). '''
		
		if struct is not None:
			self.fillStructure(struct)
		else:
			if len(kwargs) > 0:
				self.fillStructure(**kwargs)

	@classmethod
	def _type(cls):
		return cls._type
		
	@classmethod
	def serialize(cls):
		return self.__dict__
		
	@classmethod
	def deserialize(cls, structure):
		return cls(structure)
						

class DictProxy(UtilStruct):

	''' Handy little object that takes a dict and makes it accessible via var[item] and var.item formats. Also handy for caching. '''

	## Init
	def fillStructure(self, struct=None, **kwargs):
		
		''' Set it as an object directly instead of storing in _entries. '''
		
		if struct is not None:
			if isinstance(struct, dict):
				for k, v in struct.items():
					setattr(self, k, v)

			elif isinstance(struct, list):
				for k, v in struct:
					setattr(self, k, v)
		if len(kwargs) > 0:
			for k, v in kwargs.items():
				setattr(self, k, v)

	def __getitem__(self, name):
		if name in self.__dict__:
			return getattr(self, name)
		else:
			raise AttributeError

	def __setitem__(self, name, value):
		setattr(self, name, value)

	def __delitem__(self, name):
		if name in self.__dict__:
			del self.__dict__[name]
		else:
			raise AttributeError

	def __contains__(self, name):
		return name in self.__dict__

	## Utiliy Methods
	def items(self):
		return [(k, v) for k, v in self.__dict__.items()]


class ObjectProxy(UtilStruct):

	''' Same handy object as above, but stores the entries in an _entries attribute rather than the class dict.  '''

	_entries = {}
	
	def fillStruct(self, fill, **kwargs):
		
		''' If handed a dictionary or kwargs, fill _entries with e[k] = v. A list will do the same and be interpreted as a list of tuples in (k, v) format. '''
		
		if fill is not None:
			if isinstance(fill, dict):
				for k, v in fill.items():
					self._entries[k] = v
			elif isinstance(fill, list):
				for k, v in fill:
					self._entries[k] = v
		if len(kwargs) > 0:
			for k, v in kwargs.items():
				self._entries[k] = v	

	def __getitem__(self, name):
		if name in self._entries:
			return self._entries[name]
		else:
			raise KeyError

	def __delitem__(self, name):
		if name in self._entries:
			del self._entries[name]

	def __getattr__(self, name):
		return self._entries.get(name)

	def __contains__(self, name):
		return name in self._entries

	def __delattr__(self, name):
		if name in self._entries:
			del self._entries[name]

	## Utiliy Methods
	def items(self):
		return [(k, v) for k, v in self._entries.items()]


class CallbackProxy(ObjectProxy):

	''' Handy little object that takes a dict and makes it accessible via var[item], but returns the result of an invoked callback(item). '''

	callback = None

	def __init__(self, callback, struct={}, **kwargs):

		''' Map the callback and fillStructure if we get one via `struct`. '''

		self.callback = callback

		if struct is not None:
			self._entries = struct
		else:
			if len(kwargs) > 0:
				self._entries = dict([i for i in struct.items()]+[i for i in kwargs.items()])

	def __getitem__(self, name):
		if name in self._entries:
			return self.callback(self._entries.get(name))
		else:
			raise KeyError

	def __getattr__(self, name):
		return self.callback(self._entries.get(name))