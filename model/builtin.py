from apptools.model import ndb

## Builtin Models


# This model keeps track of async sessions established by the service layer.
class UserServicePushSession(ndb.Model):

    ''' This model keeps track of async sessions established by the service layer. '''

    seed = ndb.StringProperty()
    token = ndb.StringProperty()
