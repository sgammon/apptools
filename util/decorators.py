# -*- coding: utf-8 -*-

"""
-----------------------------
apptools2: utility decorators
-----------------------------

this package provides useful decorators that crosscut the regular
functional bounds of apptools' main packages. stuff in here is
generally used everywhere.

:author: Sam Gammon (sam@momentum.io)
:copyright: (c) 2013 momentum labs.
:license: This is private source code - Ampush has been granted an
          unlimited, exclusive license for embedded use. For details
          about embedded licenses and other legalese, see `LICENSE.md`.
"""


## ``classproperty`` - use like ``@property``, but at the class-level.
class classproperty(property):

    ''' Custom decorator for class-level property getters.
        Usable like ``@property`` and chainable with
        ``@memoize``, as long as ``@memoize`` is used as
        the inner decorator. '''

    def __get__(self, instance, owner):

        ''' Return the property value at the class level.

            :param instance: Current encapsulating object
                             dispatching via the descriptor
                             protocol, ``None`` if we are
                             being dispatched from the
                             class level.

            :param owner: Corresponding owner type, available
                          whether we're dispatching at the
                          class or instance level.

            :returns: Result of a ``classmethod``-wrapped,
                      ``property``-decorated method. '''

        return classmethod(self.fget).__get__(None, owner)()


## ``memoize`` - cache the output of a property descriptor call
class memoize(property):

    ''' Custom decorator for property memoization. Usable
        like ``@property`` and chainable with ``@classproperty``,
        the utility decorator above. '''

    _value = None
    __initialized__ = False

    def __get__(self, instance, owner):

        ''' If we have a cached value attached to this
            context, return it.

            :param instance: Current encapsulating object
                             dispatching via the descriptor
                             protocol, or ``None`` if we
                             are being dispatched from the
                             class level.

            :param owner: Owner type for encapsulating
                          object, if dispatched at the
                          instance level.

            :raises: Re-raises all exceptions encountered
                     in the case of an unexpected state during
                     delegated property dispatch.

            :returns: Cached value, if any. If there is
                      no cached value, defers to decorated
                      method. '''

        if not self.__initialized__:

            try:
                if isinstance(self.fget, classproperty):
                    self._value = classmethod(self.fget.fget).__get__(None, owner)()
                else:
                    self._value = self.fget.__get__(instance, owner)()
            except:
                raise
            else:
                self.__initialized__ = True

        return self._value
