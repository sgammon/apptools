# -*- coding: utf-8 -*-

'''

Models: Builtin

Holds builtin models that are used by AppTools or AppTools extensions.

-sam (<sam@momentum.io>)

'''


from apptools.model import ndb

## Builtin Models


# This model keeps track of StoredAssets.
class StoredAsset(ndb.Model):

    ''' This model keeps track of a single item uploaded to the Blobstore or Cloud Storage. '''

    filename = ndb.StringProperty()
    blobkey = ndb.BlobKeyProperty()
    serve_url = ndb.StringProperty()
    cdn_url = ndb.StringProperty()
    content_type = ndb.StringProperty()


# This model keeps track of blobstore upload sessions.
class UploadSession(ndb.Model):

    ''' This model keeps track of blobstore upload sessions. '''

    token = ndb.StringProperty(indexed=True)
    upload_url = ndb.StringProperty(indexed=False)
    created = ndb.DateTimeProperty(indexed=False)
    enable_cdn = ndb.BooleanProperty()
    assets = ndb.KeyProperty(repeated=True)
    status = ndb.StringProperty(choices=['pending', 'success', 'fail'], indexed=True)


# This model keeps track of async sessions established by the service layer.
class PushSession(ndb.Model):

    ''' This model keeps track of async sessions established by the service layer. '''

    seed = ndb.StringProperty()
    token = ndb.StringProperty()
    active = ndb.BooleanProperty(default=True, indexed=True)
