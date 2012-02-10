# -*- coding: utf-8 -*-
import logging

_loggers = {}


class AppToolsLogController(object):

    ''' Logging controller for outputting debug information from different levels of AppTools. '''

    channel_name = '_default_'

    _severity_map = {

        'debug': logging.debug,
        'info': logging.info,
        'warning': logging.warning,
        'error': logging.error,
        'critical': logging.critical

    }

    def __init__(self, name='apptools.default'):
        self.channel_name = name

    def _send_log(self, message, module=None, severity='info'):

        ''' Output an AppTools log message. '''

        out_message = []
        if module is not None:
            out_message.append('[' + str(module) + ']')
        out_message.append(severity.upper() + ':')
        out_message.append(message)
        return self._severity_map.get(severity)(' '.join(out_message))

    def debug(self, message, module=None):
        ''' `Debug` severity. '''
        return self._send_log(message, module, 'debug')

    def info(self, message, module=None):
        ''' `Info` severity. '''
        return self._send_log(message, module, 'info')

    def warning(self, message, module=None):
        ''' `Warning` severity. '''
        return self._send_log(message, module, 'warning')

    def error(self, message, module=None):
        ''' `Error` severity. '''
        return self._send_log(message, module, 'error')

    def critical(self, message, module=None):
        ''' `Critical` severity. '''
        return self._send_log(message, module, 'critical')
