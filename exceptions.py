# -*- coding: utf-8 -*-

'''

AppTools Exceptions

Holds exceptions that can happen inside AppTools (AppToolsException) and in the user's
app (AppException).

-sam (<sam@momentum.io>)

'''


## AppException
# Userland exceptions should extend this to hook into AppTools' error handling & routing.
class AppException(Exception):

    ''' All app exceptions should inherit from this. '''

    pass


## AppToolsException
# All internal/plugin AppTools exceptions extend this.
class AppToolsException(Exception):

    ''' All AppTools exceptions should inherit from this. '''

    pass
