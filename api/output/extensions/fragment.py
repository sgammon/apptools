# -*- coding: utf-8 -*-

'''

    apptools output extensions: fragment

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


# 3rd party
from jinja2 import nodes
from config import config

# apptools
from apptools.util import debug
from apptools.api.output.extensions import OutputExtension


## Globals
logger = debug.AppToolsLogger(path='apptools.api.output.extensions', name='fragment')

try:
    from google.appengine.api import memcache
except ImportError as e:
    try:
        import memcache
    except ImportError as e:
        try:
            import umemcache as memcache
        except ImportError as e:
            logger.critical('No memcache adapter found!')
            pass
    _APPENGINE = False
else:
    _APPENGINE = True

_extensionConfig = config.get('apptools.output.extension.FragmentCache')


## DynamicContentExtension
class FragmentCache(OutputExtension):

    ''' Extends Jinja2 to support custom fatcatmap dynamic content tags. '''

    tags = set(['cache'])

    def __init__(self, environment):

        ''' Extend the attached environment. '''

        super(FragmentCache, self).__init__(environment)

        # add the defaults to the environment
        environment.extend(
            fragment_cache_prefix=_extensionConfig.get('config', {}).get('prefix', 'tpl_fragment_cache'),
            fragment_cache=memcache.Client()
        )

    def parse(self, parser):

        ''' Jinja2 Parse Hook '''

        # the first token is the token that started the tag.  In our case
        # we only listen to ``'cache'`` so this will be a name token with
        # `cache` as value.  We get the line number so that we can give
        # that line number to the nodes we create by hand.
        lineno = parser.stream.next().lineno

        # now we parse a single expression that is used as cache key.
        args = [parser.parse_expression()]

        # if there is a comma, the user provided a timeout.  If not use
        # None as second parameter.
        if parser.stream.skip_if('comma'):
            args.append(parser.parse_expression())
        else:
            args.append(nodes.Const(None))

        # now we parse the body of the cache block up to `endcache` and
        # drop the needle (which would always be `endcache` in that case)
        body = parser.parse_statements(['name:endcache'], drop_needle=True)

        # now return a `CallBlock` node that calls our _cache_support
        # helper method on this extension.
        return nodes.CallBlock(self.call_method('_cache_support', args),
                               [], [], body).set_lineno(lineno)

    def _cache_support(self, name, timeout, caller):

        ''' Helper callback. '''

        key = '//'.join([self.environment.fragment_cache_prefix, name])

        # try to load the block from the cache
        # if there is no fragment in the cache, render it and store
        # it in the cache.
        rv = self.environment.fragment_cache.get(key)
        if rv is not None:
            return rv
        rv = caller()
        if timeout is not None:
            self.environment.fragment_cache.add(key, rv, timeout)
        else:
            self.environment.fragment_cache.add(key, rv)
        return rv
