# -*- coding: utf-8 -*-

'''

Models: Builtin

Holds builtin models that are used by AppTools or AppTools extensions.

-sam (<sam@momentum.io>)

'''


# Base Imports
import datetime

# AppTools Model API
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


######## ======== XMS Content Models ======== ########

## ContentNamespace
# Groups runtime sections of dynamic content, if not assigned a datastore key as a namespace.
class ContentNamespace(model.ThinModel):

    ''' Represents a group of ContentAreas namespaced by something other than a datastore key (otherwise they are put under that and just correlated here). '''

    # Storage Settings
    name = basestring, {'required': True, 'indexed': True}
    areas = model.ThinKey, {'repeated': True, 'indexed': True}
    target = model.ThinKey, {'default': None}


## ContentArea
# Marks an editable dynamic area on a given page for a given data point.
class ContentArea(model.ThinModel):

    ''' Represents a content area that can be edited for a certain datapoint. '''

    html = basestring, {'impl': 'TextProperty'}
    text = basestring, {'impl': 'TextProperty'}
    local = bool, {'default': False}
    latest = model.ThinKey, {'default': None}
    versions = model.ThinKey, {'repeated': True}


## ContentSnippet
# A content value for a content area (multiple exist for an area only for versioned content sections).
class ContentSnippet(model.ThinModel):

    ''' Represents a versioned content value of a content area. '''

    area = model.ThinKey
    html = basestring, {'impl': 'TextProperty', 'compressed': True}
    text = basestring, {'impl': 'TextProperty', 'compressed': True}
    summary = model.ThinKey


## ContentSummary
# A shortened summary value for a content area's content.
class ContentSummary(model.ThinModel):

    ''' Represents a summary of content in a content area. '''

    target = model.ThinKey
    html = basestring, {'impl': 'BlobProperty'}
    text = basestring, {'impl', 'TextProperty'}
