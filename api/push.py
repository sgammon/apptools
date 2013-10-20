# -*- coding: utf-8 -*-

'''

    apptools API: push

    bridges the AppEngine Channel API into base classes via `PushMixin`.
    this adds the methods + properties:

        - _servicesConfig: Shortcut to project services config.
        - _globalServicesConfig: Shortcut to global Service Layer settings.
        - make_services_manifest: Generate a datastructure of installed + enabled services, suitable for
            mapping to URLs or printing to a template.

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


# Base Imports
import random
import hashlib
from apptools.util import datastructures

# Mixin Imports
from apptools.api import CoreAPI
from apptools.api import HandlerMixin


## CorePushAPI
# Ties together all the pieces needed for proper server => client push communications.
class CorePushAPI(CoreAPI):

    ''' Contains core server=>client push features. '''

    def create_channel(self, cid, duration):

        ''' Just pass-through to Channel API for now. '''

        from google.appengine.api import channel
        return channel.create_channel(cid, duration)

_api = CorePushAPI()


## PushMixin
# Used as an addon class to base classes to bridge in access to Push API functionality.
class PushMixin(HandlerMixin):

    ''' Bridges the AppEngine Channel API and base classes. '''

    _push_api = _api
    push = datastructures.ObjectProxy({

        'cid': None,
        'token': None,
        'session': None

    })

    def preload(self, cid=None, token=None, duration=120):

        ''' Preloads the session + template contexts with either a given or generated Channel token. '''

        if token is None:
            if cid is None:
                cid = self.request.environ.get('REQUEST_ID_HASH', hashlib.sha256(random.random() * random.random()).hexdigest())
            token = self._push_api.create_channel(cid, duration)

        self.push.cid = cid
        self.push.token = token
        self.push.session = True

        return cid, token
