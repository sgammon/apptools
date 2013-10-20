# -*- coding: utf-8 -*-

'''

    apptools model: builtins

    holds builtin models that are used by AppTools or AppTools extensions.

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
import datetime

# AppTools Model API
from apptools import model


## Builtin Models


## StoredAsset
# This model keeps track of StoredAssets.
class StoredAsset(model.Model):

    ''' This model keeps track of a single item uploaded to the Blobstore or Cloud Storage. '''

    filename = basestring
    blobkey = basestring, {'impl': 'BlobKeyProperty'}
    serve_url = basestring
    cdn_url = basestring
    content_type = basestring


## UploadSession
# This model keeps track of file upload sessions.
class UploadSession(model.Model):

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
class PushSession(model.Model):

    ''' This model keeps track of async sessions established by the service layer. '''

    seed = basestring
    token = basestring
    active = bool, {'default': True}


######## ======== XMS Content Models ======== ########

## ContentNamespace
# Groups runtime sections of dynamic content, if not assigned a datastore key as a namespace.
class ContentNamespace(model.Model):

    ''' Represents a group of ContentAreas namespaced by something other than a datastore key (otherwise they are put under that and just correlated here). '''

    # Storage Settings
    name = basestring, {'required': True, 'indexed': True}
    areas = model.Key, {'repeated': True, 'indexed': True}
    target = model.Key, {'default': None}


## ContentArea
# Marks an editable dynamic area on a given page for a given data point.
class ContentArea(model.Model):

    ''' Represents a content area that can be edited for a certain datapoint. '''

    html = basestring, {'impl': 'TextProperty'}
    text = basestring, {'impl': 'TextProperty'}
    local = bool, {'default': False}
    latest = model.Key, {'default': None}
    versions = model.Key, {'repeated': True}


## ContentSnippet
# A content value for a content area (multiple exist for an area only for versioned content sections).
class ContentSnippet(model.Model):

    ''' Represents a versioned content value of a content area. '''

    area = model.Key
    html = basestring, {'impl': 'TextProperty', 'compressed': True}
    text = basestring, {'impl': 'TextProperty', 'compressed': True}
    summary = model.Key


## ContentSummary
# A shortened summary value for a content area's content.
class ContentSummary(model.Model):

    ''' Represents a summary of content in a content area. '''

    target = model.Key
    html = basestring, {'impl': 'BlobProperty'}
    text = basestring, {'impl': 'TextProperty'}
