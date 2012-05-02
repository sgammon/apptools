# -*- coding: utf-8 -*-

'''

Services: Messages

Holds built in message classes for services that are enabled by default as
part of the AppTools Service Layer framework.

-sam (<sam@momentum.io>)

'''

from protorpc import messages


#+#+#+ ==== System API Messages ==== +#+#+#
class Echo(messages.Message):

    ''' I am rubber and you are glue... '''

    message = messages.StringField(1, default='Hello, World!')


class HelloRequest(messages.Message):

    ''' A bit more personal than Echo. '''

    name = messages.StringField(1, default='AppTools')


class WhoAreYouResponse(messages.Message):

    ''' Returns basic fingerprint info about this app, and the infrastructure that responded to this request. '''

    class GatewayInterface(messages.Enum):

        ''' Describes the server standard used to serve this request. '''

        CGI = 0
        WSGI = 1

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


class ManifestRequest(messages.Message):

    ''' Requests a manifest, of any type. '''

    base_version = messages.StringField(1)
    last_modified = messages.StringField(2)


class ServiceManifestResponse(messages.Message):

    ''' Responds to a request for a services manifest. '''

    class APIService(messages.Message):

        ''' Represents an API service. '''

        class ServiceOpts(messages.Message):

            ''' Config values for JS-side service stuff. '''

            caching = messages.BooleanField(1)
            tick = messages.BooleanField(2)
            tick_action = messages.StringField(3)
            tick_interval = messages.IntegerField(4)
            async = messages.BooleanField(5)

        class ProfileConfig(messages.Message):

            ''' Specifies a profile config name and value for a service. '''

            name = messages.StringField(1)
            value = messages.StringField(2)

        name = messages.StringField(1)
        rpc_url = messages.StringField(2)
        methods = messages.StringField(3, repeated=True)
        profiles = messages.MessageField(ProfileConfig, 4, repeated=True)
        opts = messages.MessageField(ServiceOpts, 5)

    version = messages.StringField(1)
    timestamp = messages.StringField(2)
    services = messages.MessageField(APIService, 3, repeated=True)


#+#+#+ ==== Assets API Messages ==== +#+#+#
class AssetRequest(messages.Message):

    ''' Requests a URL to an asset. '''

    name = messages.StringField(1)
    package = messages.StringField(2)
    version = messages.StringField(3)
    minify = messages.BooleanField(4, default=False)


class ImageRequest(messages.Message):

    ''' Requests a URL to an image. '''

    name = messages.StringField(1)
    blob = messages.StringField(2)
    size = messages.IntegerField(3)
    crop = messages.IntegerField(4)


class BlobRequest(messages.Message):

    ''' Requests a URL to download a serve a blob, by key. '''

    blob = messages.StringField(1)
    serve = messages.BooleanField(2)
    download = messages.BooleanField(3)


class AssetResponse(messages.Message):

    ''' Responds with a URL to a blob, asset, or image. '''

    serve_url = messages.StringField(1)
    download_url = messages.StringField(2)
    expiration = messages.IntegerField(3)


class AssetManifestResponse(messages.Message):

    ''' Responds with a list of assets that should be on a cache manifest. '''

    class Fallback(messages.Message):

        ''' Fallback manifest entry. '''

        fallback = messages.StringField(1, repeated=True)

    cache = messages.StringField(2, repeated=True)
    network = messages.StringField(3, repeated=True)
    fallback = messages.MessageField(Fallback, 4, repeated=True)


class UploadURLRequest(messages.Message):

    ''' Request a blobstore upload URL. '''

    pass


class UploadURLResponse(messages.Message):

    ''' Respond with a blobstore upload URL. '''

    url = messages.StringField(1)
    token = messages.StringField(2)
    ticket = messages.StringField(3)
