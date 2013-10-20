# -*- coding: utf-8 -*-

'''

    apptools util: decorators

    this package provides useful decorators that crosscut the regular
    functional bounds of apptools' main packages. stuff in here is
    generally used everywhere.

    :author: Sam Gammon <sam@momentum.io>
    :copyright: (c) momentum labs, 2013
    :license: The inspection, use, distribution, modification or implementation
              of this source code is governed by a private license - all rights
              are reserved by the Authors (collectively, "momentum labs, ltd")
              and held under relevant California and US Federal Copyright laws.
              For full details, see ``LICENSE.md`` at the root of this project.
              Continued inspection of this source code demands agreement with
              the included license and explicitly means acceptance to these terms.

'''


## ``classproperty`` - use like ``@property``, but at the class-level.
class classproperty(property):

    ''' Custom decorator for class-level property getters.
        Usable like ``@property`` and chainable with
        ``@memoize``, as long as ``@memoize`` is used as
        the inner decorator. '''

    def __get__(self, instance, owner):

        ''' Return the property value at the class level.

            :param instance: Current encapsulating object
            dispatching via the descriptor protocol,
            ``None`` if we are being dispatched from the
            class level.

            :param owner: Corresponding owner type, available
            whether we're dispatching at the class or instance
            level.

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
            dispatching via the descriptor protocol, or
            ``None`` if we are being dispatched from the
            class level.

            :param owner: Owner type for encapsulating
            object, if dispatched at the instance level.

            :raises: Re-raises all exceptions encountered
            in the case of an unexpected state during
            delegated property dispatch.

            :returns: Cached value, if any. If there is
            no cached value, defers to decorated method. '''

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


## ``config`` - markup a class for apptools structure.
def config(debug=False, path=None):

    ''' Prepare to inject config/path values
        at ``debug`` and ``path``.

        :param debug: Default value for class-level
        ``debug`` flag. Overridden in config. Defaults
        to ``False``.

        :param path: String path to configuration blob
        in main appconfig. Expected to be ``basestring``.
        Defaults to Python module/name classpath of
        injectee.

        :returns: Closure that constructs an injected
        target class. '''

    # resolve appconfig
    try:
        import config as appconfig
    except ImportError:
        class Config(object):
            debug = True
            config = {}
        appconfig = Config()

    # build injection closure
    def inject(klass):

        ''' Injection closure that prepares ``klass``
            with basic apptools structure.

            :param klass: Target class slated for injection.
            :returns: Injected class structure. '''

        def _config(cls):

            ''' Named config pipe. Resolves configuration
                at the local class' :py:attr:`cls._config_path`,
                if any, which is usually injected by apptools
                utils or provided manually.

                :returns: Configuration ``dict``, from main appconfig,
                or default ``dict`` of ``{'debug': True}``. '''

            return appconfig.config.get(cls._config_path, {'debug': True})

        def _logging(cls):

            ''' Named logging pipe. Prepares custom Logbook/Python-backed
                ``Logger`` via config path and class name. Allows fine
                grained control of logging output, even at the individual
                class level.

                :returns: Customized :py:class:`debug.AppToolsLogger` class,
                attached with injectee's module path and name (or config
                path, if configured). '''

            from apptools.util import debug

            _csplit = cls._config_path.split('.')
            return debug.AppToolsLogger(**{
                'path': '.'.join(_csplit[:-1]),
                'name': _csplit[-1]
            })._setcondition(cls.config.get('debug', True))

        # attach injected properties and classmethods
        klass._config_path = path or '.'.join((klass.__module__, klass.__name__))
        klass.config, klass.logging = classproperty(_config), classproperty(_logging)
        return klass

    return inject
