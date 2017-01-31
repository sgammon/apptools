# -*- coding: utf-8 -*-

'''

    apptools API: services

    bridges the AppTools service layer to base classes via `ServicesMixin`.
    this adds the methods + properties:

        - _servicesConfig: Shortcut to project services config.
        - _globalServicesConfig: Shortcut to global Service Layer settings.
        - make_services_manifest: Generate a datastructure of installed + enabled services, suitable for
            mapping to URLs or printing to a template.

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


# API Imports
from apptools.api import CoreAPI
from apptools.api import HandlerMixin


## CoreServicesAPI
# Ties together interaction between base classes and the Service Layer.
class CoreServicesAPI(CoreAPI):

    ''' Ties together parts required to bridge the ServiceLayer and base classes. '''

    def preload(self, *args, **kwargs):

        ''' NotImplemented '''

        raise NotImplemented


_api = CoreServicesAPI()


## ServicesMixin
# Used as an addon class to base classes to bridge in Service Layer-related functionality.
class ServicesMixin(HandlerMixin):

    ''' Exposes service-related methods to BaseHandler. '''

    _services_api = _api

    def make_services_manifest(self):

        ''' Generate a struct we can pass to the page in JSON that describes API services. '''

        from apptools import rpc

        ## Generate list of services to expose to user
        svcs = []
        opts = {}

        sdebug = self._servicesConfig.get('debug', False)

        if sdebug:
            self.logging.dev('Generating services manifest...')

        if len(self._servicesConfig.get('services', [])):
            service_specs = self._servicesConfig['services']

        else:
            service_specs = rpc._project_services['services']

        for name, config in service_specs.items():

            if sdebug:
                self.logging.dev('Considering API "%s"...' % name)
            if config['enabled'] is True:

                if sdebug:
                    self.logging.dev('API is enabled.')

                security_profile = self._globalServicesConfig.get('middleware_config', {}).get('security', {}).get('profiles', {}).get(config.get('config', {}).get('security', '__null__'), {})

                caching_profile = self._globalServicesConfig.get('middleware_config', {}).get('caching', {}).get('profiles', {}).get(config.get('config', {}).get('caching', {}))

                if security_profile is None:

                    ## Pull default profile if none is specified
                    security_profile = self._globalServicesConfig.get('middleware_config', {}).get('security', {}).get('profiles', {}).get(self._globalServicesConfig.get('defaults', {}).get('service', {}).get('config', {}).get('security', {}))

                if caching_profile is None:
                    caching_profile = self._globalServicesConfig.get('middleware_config', {}).get('caching', {}).get('profiles', {}).get(self._globalServicesConfig.get('defaults', {}).get('service', {}).get('config', {}).get('caching', {}))

                ## Add caching to local opts
                opts['caching'] = (caching_profile or {}).get('activate', {}).get('local', False)

                ## Grab prefix
                service_action = self._servicesConfig.get('config', {}).get('url_prefix', '/_api/rpc').split('/')

                ## Add service name
                service_action.append(name)

                ## Join into endpoint URL
                service_action_url = '/'.join(service_action)

                ## Expose depending on security profile
                if security_profile.get('expose', 'all') == 'all':
                    if sdebug:
                        self.logging.dev('API is exposed publicly.')
                    svcs.append((name, service_action_url, config, opts))

                elif security_profile['expose'] == 'admin':
                    if sdebug:
                        self.logging.dev('API is exposed to admins only.')
                    if self.api.users.is_current_user_admin():
                        if sdebug:
                            self.logging.dev('User valid for API access.')
                        svcs.append((name, service_action_url, config, opts))

                elif security_profile['expose'] == 'none':
                    if sdebug:
                        self.logging.dev('API is set to expose to `none`.')
                    continue
            else:
                if sdebug:
                    self.logging.dev('API is disabled.')

        return svcs
