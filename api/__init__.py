# -*- coding: utf-8 -*-

'''

AppTools APIs

Holds Core APIs and abstract API/Mixin classes to enable the creation of plugins,
extensions, mixins, and all sorts of other integration points.

-sam (<sam@momentum.io>)

'''


## Core API
# Core APIs are large chunks of functionality that AppTools can optionally perform for your application.
# The Assets API & Output API are Core APIs, along with any other major pieces of code.
class CoreAPI(object):

    ''' Used as a controller for a core feature of the AppTools framework. '''

    pass


## BaseObject API
# This is the parent class to all AppTools-exposed Base* classes (think: BaseHandler, BaseModel, BasePipeline, etc.)
class BaseObject(object):

    ''' Provides AppTools and platform-specific features to Base object classes. '''

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


## ModelMixin
# Bridges a Core API to a BaseModel.
class ModelMixin(APIMixin):

    ''' Used to bridge between a Core API and a Model, via Python's awesome support for multi-inheritance. '''

    pass


## PluginMixin
# Bridges a Core API to a BasePlugin.
class PluginMixin(APIMixin):

    ''' Used to bridge between a Core API and a Plugin, via Python's awesome support for multi-inheritance. '''

    pass
