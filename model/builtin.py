# -*- coding: utf-8 -*-

'''

Models: Builtin

Holds builtin models that are used by AppTools or AppTools extensions.

-sam (<sam@momentum.io>)

'''


import datetime
from apptools import model

## Builtin Models


## StoredAsset
# This model keeps track of StoredAssets.
class StoredAsset(model.ThinModel):

    ''' This model keeps track of a single item uploaded to the Blobstore or Cloud Storage. '''

    filename = basestring
    blobkey = basestring, {'impl': 'BlobKeyProperty'}
    serve_url = basestring
    cdn_url = basestring
    content_type = basestring


## UploadSession
# This model keeps track of file upload sessions.
class UploadSession(model.ThinModel):

    ''' This model keeps track of blobstore upload sessions. '''

    token = basestring
    upload_url = basestring
    created = datetime.datetime, {'auto_now_add': True}
    enable_cdn = bool
    assets = basestring, {'impl': 'KeyProperty'}
    backend = basestring, {'choices': ['blobstore', 'cloud']}
    status = basestring, {'choices': ['pending', 'success', 'fail']}
    

## PushSession
# This model keeps track of async sessions established by the service layer.
class PushSession(model.ThinModel):

    ''' This model keeps track of async sessions established by the service layer. '''

    seed = basestring
    token = basestring
    active = bool, {'default': True}

