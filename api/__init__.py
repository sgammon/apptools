# -*- coding: utf-8 -*-

'''

    apptools API

    holds Core APIs and abstract API/Mixin classes to enable the creation of plugins,
    extensions, mixins, and all sorts of other integration points.

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
