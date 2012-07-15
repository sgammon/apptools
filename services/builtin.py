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

# Service Imports
from apptools.services import remote
from apptools.services import messages
from apptools.services import BaseService
from apptools.services import message_types

## Message Imports
from apptools.services.messages import *

# API Imports
from apptools.api.assets import AssetsMixin

# Model Imports
from apptools.model.builtin import UploadSession


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
        response.appid = self.api.identity.get_application_id()
        response.version = '-'.join(map(lambda x: str(x), ['.'.join(map(lambda x: str(x), [project_version.get('major', 1), project_version.get('minor', 0), project_version.get('micro', 0)])), project_version.get('build', '0PRE'), project_version.get('release', 'ALPHA')]))

        # Infrastructure Info
        response.datacenter = self.request.environ.get('DATACENTER', '_default_')
        response.instance = self.request.environ.get('INSTANCE_ID', '_default_')
        response.runtime = self.request.environ.get('APPENGINE_RUNTIME', '_default_')
        if self.api.backends.get_backend() is not None:
            response.backend = self.api.backends.get_backend()
            response.backend_instance = self.api.backends.get_instance()
        response.debug = config.debug
        response.app_version = self.request.environ.get('CURRENT_VERSION_ID', '_default_')

        # Request Info
        response.request_id = self.request.environ.get('REQUEST_ID_HASH', '_default_')
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
        if hasattr(self.api.quota, 'get_request_cpu_usage'):
            response.cpu_time = self.api.quota.get_request_cpu_usage()
        response.api_time = self.api.quota.get_request_api_cpu_usage()

        # Identity Info
        response.default_hostname = self.api.identity.get_default_version_hostname()
        certificates = []
        for certificate in self.api.identity.get_public_certificates():
            certificates.append(WhoAreYouResponse.AppCertificate(keyname=certificate.key_name, x509=certificate.x509_certificate_pem))
        response.certificates = certificates
        response.service_account = self.api.identity.get_service_account_name()

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
    def image_url(self, request):

        ''' Resolve and return an image URL. '''

        pass

    @remote.method(AssetRequest, AssetResponse)
    def script_url(self, request):

        ''' Resolve and return a URL to a script. '''

        pass

    @remote.method(AssetRequest, AssetResponse)
    def style_url(self, request):

        ''' Resolve and return a URL to a stylesheet. '''

        pass

    @remote.method(BlobRequest, AssetResponse)
    def blob_url(self, request):

        ''' Resolve and return a blob URL. '''

        pass

    @remote.method(BlobRequest, AssetResponse)
    def storage_url(self, request):

        ''' Resolve and return a URL from Google Cloud Storage. '''

        pass

    @remote.method(ManifestRequest, AssetManifestResponse)
    def manifest(self, request):

        ''' Generate and return an asset manifest. '''

        pass

    @remote.method(UploadURLRequest, UploadURLResponse)
    def generate_upload_url(self, request):

        ''' Generate and return a blobstore upload URL. '''

        upload_item_token = hashlib.sha256(self.request.environ['REQUEST_ID_HASH']).hexdigest()
        upload_ticket = UploadSession(token=upload_item_token,
                                      created=datetime.datetime.now(),
                                      status='pending',
                                      upload_url=self.api.blobstore.create_upload_url('/_api/upload/callback/%s' % upload_item_token))
        upload_ticket_key = upload_ticket.put()

        return UploadURLResponse(url=upload_ticket.upload_url, token=upload_item_token, ticket=str(upload_ticket_key))
