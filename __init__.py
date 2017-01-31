# -*- coding: utf-8 -*-

'''

    apptools

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


# try the bootstrapper...
try:
    import bootstrap
    bootstrap.AppBootstrapper.prepareImports()
except:
    pass  # pragma: no cover

## AppTools Util
from apptools.util import appconfig

try:
    import config

except ImportError as e:  # pragma: no cover
    cfg = appconfig.ConfigProxy(appconfig._DEFAULT_CONFIG)

else:
    cfg = appconfig.ConfigProxy(config.config)
    config.config = cfg


## WSGI Gateway
def gateway(environ, start_response):

    ''' Central gateway into AppTools' WSGI dispatch. '''

    from apptools import dispatch  # pragma: no cover
    return dispatch.gateway(environ, start_response)  # pragma: no cover


## Expose base classes
#_apptools_servicelayer = [messages, fields, middleware, decorators]
#_apptools_base_classes = [BaseHandler, BaseModel, BaseService, BasePipeline, AppException]
#__all__ = [str(i.__class__.__name__) for i in _apptools_base_classes] + _apptools_servicelayer


## For direct/CGI...
if __name__ == '__main__':
    gateway(None, None)  # pragma: no cover
