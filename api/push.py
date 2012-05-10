# -*- coding: utf-8 -*-

'''

API: Push

Bridges the AppEngine Channel API into base classes via `PushMixin`.
This adds the methods + properties:

    - _servicesConfig: Shortcut to project services config.
    - _globalServicesConfig: Shortcut to global Service Layer settings.
    - make_services_manifest: Generate a datastructure of installed + enabled services, suitable for
        mapping to URLs or printing to a template.

-sam (<sam@momentum.io>)

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
