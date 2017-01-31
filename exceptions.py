# -*- coding: utf-8 -*-

'''

    apptools exceptions

	holds exceptions that can happen inside AppTools (AppToolsException)
	and in the user's app (AppException).

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


## AppException
# Userland exceptions should extend this to hook into AppTools' error handling & routing.
class AppException(Exception):

    ''' All app exceptions should inherit from this. '''


## AppToolsException
# All internal/plugin AppTools exceptions extend this.
class AppToolsException(Exception):

    ''' All AppTools exceptions should inherit from this. '''
