# -*- coding: utf-8 -*-

'''

Services: Messages

Holds built in message classes for services that are enabled by default as
part of the AppTools Service Layer framework.

-sam (<sam@momentum.io>)

'''

from protorpc import messages


#+#+#+ ==== System API Messages ==== +#+#+#

## Echo
# Valid as a request or response. Defaults `message` to "Hello, World!". Mainly for testing purposes.
class Echo(messages.Message):

    ''' I am rubber and you are glue... '''

    message = messages.StringField(1, default='Hello, World!')


## HelloRequest
# Used to test having different request/response classes. Usually an Echo is used to return.
class HelloRequest(messages.Message):

    ''' A bit more personal than Echo. '''

    name = messages.StringField(1, default='AppTools')


## WhoAreYouResponse
# Response for the System service that gives a bunch of debug/platform info.
class WhoAreYouResponse(messages.Message):

    ''' Returns basic fingerprint info about this app, and the infrastructure that responded to this request. '''

    ## GatewatInterface
    # Describes whether the service layer request was fulfilled via CGI or WSGI.
    class GatewayInterface(messages.Enum):

        ''' Describes the server standard used to serve this request. '''

        CGI = 0
        WSGI = 1

    ## AppCertificate
    # Describes a certificate attached to the app's identity, via the App Identity API.
    class AppCertificate(messages.Message):

        ''' Describes a public certificate provided by AppEngine for this app's identity. '''

        keyname = messages.StringField(1)
        x509 = messages.StringField(2)

    # Basic Info
    name = messages.StringField(1)
    appid = messages.StringField(2)
    version = messages.StringField(3)

    # Infrastructure Info
    datacenter = messages.StringField(4)
    instance = messages.StringField(5)
    runtime = messages.StringField(6)
    backend = messages.StringField(7)
    backend_instance = messages.StringField(8)
    debug = messages.BooleanField(9)
    app_version = messages.StringField(10)

    # Request Info
    request_id = messages.StringField(11)
    interface = messages.EnumField(GatewayInterface, 12, default='CGI')
    sdk_version = messages.StringField(13)
    runtime_version = messages.StringField(14)
    multithread = messages.BooleanField(15)
    multiprocess = messages.BooleanField(16)

    # Performance Info
    walltime = messages.IntegerField(17)
    cpu_time = messages.IntegerField(18)
    api_time = messages.IntegerField(19)

    # Identity Info
    default_hostname = messages.StringField(20)
    certificates = messages.MessageField(AppCertificate, 21, repeated=True)
    service_account = messages.StringField(22)


## ManifestRequest
# Used to request a API service or asset manifest.
class ManifestRequest(messages.Message):

    ''' Requests a manifest, of any type. '''

    base_version = messages.StringField(1)
    last_modified = messages.StringField(2)


## ServiceManifestResponse
# Used to respond to requests for API service manifests.
class ServiceManifestResponse(messages.Message):

    ''' Responds to a request for a services manifest. '''

    ## APIService
    # Represents an installed API service.
    class APIService(messages.Message):

        ''' Represents an API service. '''

        ## ServiceOpts
        # Represents a set of config options for an installed API service.
        class ServiceOpts(messages.Message):

            ''' Config values for JS-side service stuff. '''

            caching = messages.BooleanField(1)
            tick = messages.BooleanField(2)
            tick_action = messages.StringField(3)
            tick_interval = messages.IntegerField(4)
            async = messages.BooleanField(5)

        ## ProfileConfig
        # Represents a chosen middleware profile specified in config options for an installed API service.
        class ProfileConfig(messages.Message):

            ''' Specifies a profile config name and value for a service. '''

            name = messages.StringField(1)
            value = messages.StringField(2)

        # Basic Info
        name = messages.StringField(1)
        rpc_url = messages.StringField(2)
        methods = messages.StringField(3, repeated=True)

        # Options + Profiles
        profiles = messages.MessageField(ProfileConfig, 4, repeated=True)
        opts = messages.MessageField(ServiceOpts, 5)

    # Basic Info
    version = messages.StringField(1)
    timestamp = messages.StringField(2)

    # Services
    services = messages.MessageField(APIService, 3, repeated=True)
    service_count = messages.IntegerField(4)


#+#+#+ ==== Assets API Messages ==== +#+#+#

## AssetRequest
# Represents a request for a dynamic or static (registered/unregistered) asset.
class AssetRequest(messages.Message):

    ''' Requests a URL to an asset. '''

    name = messages.StringField(1)
    package = messages.StringField(2)
    version = messages.StringField(3)
    minify = messages.BooleanField(4, default=False)


## ImageRequest
# Represents a request for a dynamic or static image asset.
class ImageRequest(messages.Message):

    ''' Requests a URL to an image. '''

    name = messages.StringField(1)
    blob = messages.StringField(2)
    size = messages.IntegerField(3)
    crop = messages.IntegerField(4)


## BlobRequest
# Represents a request for a blob URL or inlined blob.
class BlobRequest(messages.Message):

    ''' Requests a URL to download a serve a blob, by key. '''

    blob = messages.StringField(1)
    serve = messages.BooleanField(2)
    download = messages.BooleanField(3)


## AssetResponse
# Represents a response to a request for a dynamic or static (registered/unregistered) asset.
class AssetResponse(messages.Message):

    ''' Responds with a URL to a blob, asset, or image. '''

    serve_url = messages.StringField(1)
    download_url = messages.StringField(2)
    expiration = messages.IntegerField(3)


## AssetManifestResponse
# Represents a response to a request for an asset manifest (used in the HTML5 AppCaching API).
class AssetManifestResponse(messages.Message):

    ''' Responds with a list of assets that should be on a cache manifest. '''

    ## Fallback
    # Represents a FALLBACK clause in an HTML5 AppCache manifest.
    class Fallback(messages.Message):

        ''' Fallback manifest entry. '''

        fallback = messages.StringField(1, repeated=True)

    # AppCache Clauses
    cache = messages.StringField(2, repeated=True)
    network = messages.StringField(3, repeated=True)
    fallback = messages.MessageField(Fallback, 4, repeated=True)


## UploadURLRequest
# Represents a request for a blobstore file upload endpoint.
class UploadURLRequest(messages.Message):

    ''' Request a blobstore upload URL. '''

    pass


## UploadURLResponse
# Represents a response to a request for a blobstore file upload endpoint.
class UploadURLResponse(messages.Message):

    ''' Respond with a blobstore upload URL. '''

    url = messages.StringField(1)
    token = messages.StringField(2)
    ticket = messages.StringField(3)
