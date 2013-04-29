from apptools.util import datastructures


class classproperty(property):

    ''' Custom decorator for class-level property getters. '''

    def __get__(self, instance, owner):

        ''' Return the property value at the class level. '''

        return classmethod(self.fget).__get__(None, owner)()
