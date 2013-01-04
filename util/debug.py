# -*- coding: utf-8 -*-

'''

Util: Debug

Holds service middleware, that can hook into the pre- or post- remote method execution
sequence.

-sam (<sam@momentum.io>)

'''

# Base Imports
import os
import logging
import inspect

# Logging Imports
from logging import handlers

# Exceptions
from apptools.exceptions import AppException

# Debug mode
debug = any([os.environ.get('SERVER_SOFTWARE', 'Default').startswith(x) for x in frozenset(('Develop', 'Sandbox'))])

# Datastructures
from apptools.util.datastructures import DictProxy
from apptools.util.datastructures import ObjectDictBridge
from apptools.util.datastructures import WritableObjectProxy

## Logbook Integration
# If supported, AppTools will use [Logger](http://packages.python.org/Logbook/index.html).
try:
    import logbook
except ImportError:
    _logbook_support = False

    class AppToolsLoggingEngine(logging.getLoggerClass()):

        ''' Simple, non-Logbook AppTools logging backend. '''

        pass
else:
    _logbook_support = True

    class AppToolsLoggingEngine(logbook.Logger):

        ''' Logbook-powered AppTools logging backend. '''

        pass

_loggers = WritableObjectProxy({})
_root_logger = None


## LoggingException
# Thrown if there's a serious config issue with logging. Generates a warning instead of a full runtime exception
# if it so happens that we're running on production.
class LoggingException(AppException):
    pass


## AppToolsLogger
# Represents a logging channel for a single module.
class AppToolsLogger(AppToolsLoggingEngine):

    ''' Logging controller for outputting debug information from different levels of AppTools. '''

    # Logging channel config
    name = 'apptools'
    channel_name = '_root_'
    channel_path = 'apptools'
    channel_parent = None

    # Event/context config
    bubble = False
    filters = []
    handlers = []
    disabled = False
    propagate = False
    context_fn = None
    conditional = debug
    logbook_support = False

    provider = None
    _stdlib_severity_map = DictProxy({

        'dev': logging.debug,
        'debug': logging.debug,
        'verbose': logging.debug,
        'info': logging.info,
        'warning': logging.warning,
        'error': logging.error,
        'critical': logging.critical

    })

    def __new__(cls, path='apptools', name='_root_', parent_channel=None, bubble=False, ctx=None):

        ''' Create a new logger channel, or return it if it already exists. '''

        global _loggers
        global _root_logger

        from apptools.util import appconfig

        if debug:
            default_handler = logging.StreamHandler()
        else:
            # Quick fix/patch to allow initialization here or in config
            _syslog_config = dict([(k, v) for k, v in appconfig._SYSLOG_CONFIG.items() if k not in ('class', 'level')])

            default_handler = handlers.SysLogHandler(**_syslog_config)

        if cls.handlers == []:
            cls.handlers.append(default_handler)

        if cls.__name__ == 'AppToolsLogController':
            logging.warning('AppToolsLogController is deprecated. Check logger path/name: (%s, %s).' % path, name)
        if path not in frozenset([False, None, True, '']) and isinstance(path, basestring):
            if name not in frozenset([False, None, True, '']) and isinstance(path, basestring):
                logger_k = path, name
            else:
                logger_k = (path,)

            ## check for cached logger object
            if logger_k in _loggers.keys():
                return _loggers[logger_k]
            else:
                ## splice in root as parent if unspecified
                if not parent_channel and parent_channel != False:
                    parent_channel = _root_logger

                ## explicit flag for parent-less channel
                elif parent_channel == False:
                    parent_channel = None

                return super(AppToolsLogger, cls).__new__(cls, path, name, parent_channel, bubble, ctx)

    def __init__(self, path='apptools.default', name='_default_', parent_channel=None, bubble=False, ctx=None):

        ''' Init a new logger channel. '''

        global _loggers
        global _logbook_support

        # Copy over name, path, and setup logbook (if present)
        self.logbook_support = _logbook_support
        self.channel_path, self._channel_name, self.channel_parent, self.bubble, self.context_fn = path, name, parent_channel, bubble, ctx

        if _logbook_support:

            # Init logbook properly
            super(AppToolsLogger, self).__init__(name)

            # Set provider to self (this class is a logbook logger)
            self.provider = ObjectDictBridge(super(AppToolsLogger, self))
        else:

            # Set provider to stdlib
            self.provider = self._stdlib_severity_map

        # Register this logger in the _loggers manager
        if path not in frozenset([False, None, True, '']) and isinstance(path, basestring):
            if name not in frozenset([False, None, True, '']) and isinstance(path, basestring):
                logger_k = path, name
            else:
                logger_k = (path,)
            _loggers[logger_k] = self

    def extend(self, path=None, name=None, bubble=False, ctx=None):

        ''' Extend an existing LogChannel into a new one. '''

        try:
            if path is not None and name is None:
                # If we have a path and no name, join the new path to the old one and pass only the new path in.
                return self.__class__(''.join(self.channel_path.split('.') + path.split('.')), parent_channel=self, bubble=bubble, ctx=ctx)
            elif (path is None and name is not None):
                # If we have a name and no path, pass the old path in with (with the old name included), the new name instead of the old one.
                return self.__class__(path=self.channel_path, name=name, parent_channel=self, bubble=bubble, ctx=ctx)
            elif (path is not None and name is not None):
                # If we have a path and a name, append the path to the old one, and pass in the compiled path and new name.
                appended_path = ''.join(self.channel_path.split('.') + path.split('.'))
                return self.__class__(path=appended_path, name=name, parent_channel=self, bubble=bubble, ctx=ctx)
            else:
                raise LoggingException('Cannot extend logging channel without appending a name or a path.')
        except LoggingException, e:
            if debug:
                raise e
            else:
                logging.warning('LoggingException encountered: "%s".' % e)
                logging.warning('Using stdlib fallback.')
                logging.critical('AppTools logging could not be started for path "%s"/name "%s".' % path, name)
                return logging

    def _setcondition(self, conditional):

        ''' Set a local flag to enable/disable logging through this pipe. '''

        self.conditional = conditional
        return self

    def _send_log(self, message, module=None, severity='info'):

        ''' Output an AppTools log message. '''

        if self.conditional:
        
            out_message = []
            if module is not None:
                out_message.append('[' + str(module) + ']')
            out_message.append(message)

            if _logbook_support:
                record = self.make_record_and_handle(getattr(logbook, severity.upper()), out_message, [], {}, None, {})
            else:
                # gather callee info
                frame = inspect.getframeinfo(inspect.currentframe().f_back)
                record = self.makeRecord(self.name, getattr(logging, severity.upper()), frame.filename, frame.lineno, out_message, {}, None, frame.function)
                self.handle(record)
        return

    def dev(self, message, module=None):

        ''' `Development` severity. '''

        if debug:
            return self._send_log(message, module, 'info')

    def debug(self, message, module=None):

        ''' `Debug` severity. '''

        if debug:
            return self._send_log(message, module, 'info')
        else:
            return self._send_log(message, module, 'debug')

    def verbose(self, message, module=None):

        ''' `Verbose` severity. '''

        if debug:
            return self._send_log(message, module, 'info')
        else:
            return self._send_log(message, module, 'debug')

    def info(self, message, module=None):

        ''' `Info` severity. '''

        return self._send_log(message, module, 'info')

    def warning(self, message, module=None):

        ''' `Warning` severity. '''

        return self._send_log(message, module, 'warning')

    def error(self, message, module=None, exc_info=None):

        ''' `Error` severity. '''

        return self._send_log(message, module, 'error')

    def exception(self, message, exc_info=None):

        ''' `Exception` severity. '''

        return self._send_log(message, None, 'error')

    def critical(self, message, module=None):

        ''' `Critical` severity. '''

        return self._send_log(message, module, 'critical')

    @staticmethod
    def echo(*args):

        ''' Simply print the given arguments. Used for debugging. '''

        print args


## alias for backwards compatibility
AppToolsLogController = AppToolsLogger

## create root logger
_root_logger = AppToolsLogger(path='apptools', name='', parent_channel=False)
