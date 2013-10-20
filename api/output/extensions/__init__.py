# -*- coding: utf-8 -*-

'''

    apptools output extensions

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


# jinja2
from jinja2 import ext


## OutputExtension
class OutputExtension(ext.Extension):

    ''' Abstract parent for all openfire output extensions. '''
