# -*- coding: utf-8 -*-

'''

AppTools Exceptions

Holds exceptions that can happen inside AppTools (AppToolsException) and in the user's
app (AppException).

-sam (<sam@momentum.io>)

'''


class AppException(Exception):

    ''' All app exceptions should inherit from this. '''

    pass


class AppToolsException(Exception):

    ''' All AppTools exceptions should inherit from this. '''

    pass
