from apptools.util import datastructures


class classproperty(property):

	''' Custom decorator for class-level property getters. '''

	def __get__(self, cls, owner):

		''' Return the property value at the class level. '''

		return self.fget.__get__(None, owner)(owner())

