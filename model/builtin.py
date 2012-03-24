from apptools.model import ndb

## Builtin Models


# This model keeps track of blobstore upload sessions.
class UploadSession(ndb.Model):

    ''' This model keeps track of blobstore upload sessions. '''

    token = ndb.StringProperty(indexed=True)
    upload_url = ndb.StringProperty(indexed=False)
    created = ndb.DateTimeProperty(indexed=False)
    status = ndb.StringProperty(choices=['pending', 'success', 'fail'], indexed=False)


# This model keeps track of async sessions established by the service layer.
class PushSession(ndb.Model):

    ''' This model keeps track of async sessions established by the service layer. '''

    seed = ndb.StringProperty()
    token = ndb.StringProperty()
    active = ndb.BooleanProperty(default=True, indexed=True)
