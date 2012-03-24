# -*- coding: utf-8 -*-


## Core API
# Core APIs are large chunks of functionality that AppTools can optionally perform for your application.
# The Assets API & Output API are Core APIs, along with any other major pieces of code.
class CoreAPI(object):

    ''' Used as a controller for a core feature of the AppTools framework. '''

    pass


## Mixin Framework
# Mixin classes add functionality in AppTools to other classes.
class APIMixin(object):

    ''' Used to bridge between a Core API and any other class. '''

    pass


## HandlerMixin
# Bridges a Core API to a BaseHandler.
class HandlerMixin(APIMixin):

    ''' Used to bridge between a Core API and a Handler, via Python's awesome support for multi-inheritance. '''

    pass


## PipelineMixin
# Bridges a Core API to a BasePipeline.
class PipelineMixin(APIMixin):

    ''' Used to bridge between a Core API and a Handler, via Python's awesome support for multi-inheritance. '''

    pass


## ModelMixin
# Bridges a Core API to a BaseModel.
class ModelMixin(APIMixin):

    ''' Used to bridge between a Core API and a Handler, via Python's awesome support for multi-inheritance. '''

    pass


## ServiceMixin
# Bridges a Core API to a BaseService.
class ServiceMixin(APIMixin):

    ''' Used to bridge between a Core API and a Handler, via Python's awesome support for multi-inheritance. '''

    pass
