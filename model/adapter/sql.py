# -*- coding: utf-8 -*-

'''

    apptools model adapter: SQL

	allows apptools models to be used across
	SQL tables, with enhanced mySQL support.

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


# adapter API
from .abstract import ModelAdapter


## SQLAdapter
# Adapt apptools models to SQL-like engines.
class SQLAdapter(ModelAdapter):

    ''' Adapt model classes to SQL. '''

    @classmethod
    def is_supported(cls):

        ''' Check whether this adapter is supported in the current environment. '''

        return False
