# -*- coding: utf-8 -*-

'''

Services: Builtin

Holds service APIs that are embedded in AppTools. By default, this includes the
SystemService ($.apptools.api.system), and the AssetService ($.apptools.api.assets).

-sam (<sam@momentum.io>)

'''

# Basic Imports
import time
import sys
import config
import hashlib
import datetime

# ProtoRPC Imports
from protorpc import messages
from protorpc import message_types

# Service Imports
from apptools.services import Echo
from apptools.services import remote
from apptools.services import BaseService

# API Imports
from apptools.api.assets import AssetsMixin

# Model Imports
from apptools.model.builtin import UploadSession


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


## ContentFormat
# Keeps track of available content formats for the dynamic content tools.
class ContentFormat(messages.Enum):

    ''' Specifies available formats under which content can be saved/retrieved. '''

    TEXT = 1  # sentinel for plaintext content
    HTML = 2  # sentinel for richtext content


## ContentSummary
# Summarizes a ContentSnippet entry.
class ContentSummary(messages.Message):

    ''' Describe a human-understandable summary of a content snippet. '''

    text = messages.StringField(1)
    html = messages.StringField(2)


## ContentSnippet
# Full content message, for a revision of a ContentArea.
class ContentSnippet(messages.Message):

    ''' Describe a snippet of dynamic content. '''

    html = messages.StringField(1)
    text = messages.StringField(2)
    summary = messages.MessageField(ContentSummary, 3)


## ContentArea
# An area of editable content, either plaintext/richtext
class ContentArea(messages.Message):

    ''' Describe a zone of dynamic content. '''

    pass


#+#+#+ ==== System API Service ==== +#+#+#

## SystemService
# Offers programmatic access to system services, info, and audit data.
class SystemService(BaseService):

    ''' Builtin API service for useful info/utility methods. Only exposed to logged-in app administrators by default (see config/services.py). '''

    @remote.method(Echo, Echo)
    def echo(self, request):

        ''' Just return whatever we're given. '''

        return Echo(message=request.message)

    @remote.method(HelloRequest, Echo)
    def hello(self, request):

        ''' Return whatever we're given, but with a polite hello back. '''

        return Echo(message="Hello, %s!" % request.name)

    @remote.method(message_types.VoidMessage, WhoAreYouResponse)
    def whoareyou(self, request):

        ''' Return a bunch of information about the backend. '''

        response = WhoAreYouResponse()

        project = config.config.get('apptools.project')
        project_version = project.get('version')

        # Basic Info
        response.name = project.get('name', 'AppTools')
        if hasattr(self, 'api') and hasattr(self.api, 'identity'):
            response.appid = self.api.identity.get_application_id()

            # Identity Info
            response.default_hostname = self.api.identity.get_default_version_hostname()
            certificates = []
            for certificate in self.api.identity.get_public_certificates():
                certificates.append(WhoAreYouResponse.AppCertificate(keyname=certificate.key_name, x509=certificate.x509_certificate_pem))
            response.certificates = certificates
            response.service_account = self.api.identity.get_service_account_name()

        else:
            if hasattr(config, 'appname'):
                response.appid = config.appname
            elif config.config.get('apptools.project'):
                response.appid = config.config.get('apptools.project').get('name', 'apptools')
            else:
                response.appid = 'apptools'
        response.version = '-'.join(map(lambda x: str(x), ['.'.join(map(lambda x: str(x), [project_version.get('major', 1), project_version.get('minor', 0), project_version.get('micro', 0)])), project_version.get('build', '0PRE'), project_version.get('release', 'ALPHA')]))

        # Infrastructure Info
        response.datacenter = self.request.environ.get('DATACENTER', os.environ.get('DATACENTER', '_default_'))
        response.instance = self.request.environ.get('INSTANCE_ID', os.environ.get('INSTANCE_ID', '_default_'))
        response.runtime = self.request.environ.get('APPENGINE_RUNTIME', os.environ.get('RUNTIME', '_default_'))

        if hasattr(self, 'api') and hasattr(self.api, 'backends'):
            if self.api.backends.get_backend() is not None:
                response.backend = self.api.backends.get_backend()
                response.backend_instance = self.api.backends.get_instance()
        response.debug = config.debug
        response.app_version = self.request.environ.get('CURRENT_VERSION_ID', os.environ.get('CURRENT_VERSION_ID', '_default_'))

        # Request Info
        response.request_id = self.request.environ.get('REQUEST_ID_HASH', self.request.headers.get('XAF-Request-ID', '_default_'))
        if self.request.environ.get('wsgi.version', False) is not False:
            response.interface = WhoAreYouResponse.GatewayInterface.WSGI
            response.multithread = bool(self.request.environ.get('wsgi.multithread', False))
            response.multiprocess = self.request.environ.get('wsgi.multiprocess', False)
        else:
            response.interface = WhoAreYouResponse.GatewayInterface.CGI
            response.multithread = False
            response.multiprocess = False

        response.sdk_version = self.request.environ.get('SERVER_SOFTWARE', '_default_')
        response.runtime_version = sys.version

        # Performance Info
        response.walltime = int((time.time() - self.request.clock.get('threadstart')) * 100000)
        if hasattr(self, 'api') and hasattr(self.api, 'quota'):
            if hasattr(self.api.quota, 'get_request_cpu_usage'):
                response.cpu_time = self.api.quota.get_request_cpu_usage()
            response.api_time = self.api.quota.get_request_api_cpu_usage()

        return response

    @remote.method(ManifestRequest, ServiceManifestResponse)
    def manifest(self, request):

        ''' Generate and return a services manifest. '''

        pass


#+#+#+ ==== Asset API Service ==== +#+#+#

## AssetsService
# Provides programmatic access to dynamic assets and URLs to registered/unregistered static assets.
class AssetsService(BaseService, AssetsMixin):

    ''' Builtin API service for retrieving asset URLs. Exposed publicly by default (see config/services.py). '''

    @remote.method(ImageRequest, AssetResponse)
    def image(self, request):

        ''' Resolve and return an image URL. '''

        pass

    @remote.method(AssetRequest, AssetResponse)
    def script(self, request):

        ''' Resolve and return a URL to a script. '''

        pass

    @remote.method(AssetRequest, AssetResponse)
    def style(self, request):

        ''' Resolve and return a URL to a stylesheet. '''

        pass

    @remote.method(BlobRequest, AssetResponse)
    def blob(self, request):

        ''' Resolve and return a blob URL. '''

        pass

    @remote.method(BlobRequest, AssetResponse)
    def storage(self, request):

        ''' Resolve and return a URL from Google Cloud Storage. '''

        pass

    @remote.method(ManifestRequest, AssetManifestResponse)
    def manifest(self, request):

        ''' Generate and return an asset manifest. '''

        pass

    @remote.method(UploadURLRequest, UploadURLResponse)
    def upload(self, request):

        ''' Generate and return a blobstore upload URL. '''

        upload_item_token = hashlib.sha256(self.request.environ['REQUEST_ID_HASH']).hexdigest()
        upload_ticket = UploadSession(token=upload_item_token,
                                      created=datetime.datetime.now(),
                                      status='pending',
                                      upload_url=self.api.blobstore.create_upload_url('/_api/upload/callback/%s' % upload_item_token))
        upload_ticket_key = upload_ticket.put()

        return UploadURLResponse(url=upload_ticket.upload_url, token=upload_item_token, ticket=str(upload_ticket_key))
