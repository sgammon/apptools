# -*- coding: utf-8 -*-

'''
"**apptools**" is a library for developing webapps utilizing [Google App Engine](http://code.google.com/appengine)'s
[Python](http://python.org) runtime.

Apptools is [open source](http://github.com/sgammon/apptools), and can be used on its own, or as an integrated component in a suite of tools called the [AppEngine Toolkit](http://apptools.github.com).

To use apptools, all you need to do is **extend a few base classes** into your app. The base classes provide tons of useful utilities, and handle most of the boilerplate
work you'd do anyway at the start of a new project.

There's also an **integrated [Output API](api/output.html)**, and a hybrid **registered/unregistered [Assets API](api/assets.html)**.
'''

## Base Classes
# Check out the base classes:
'''
- **BaseHandler**, in [core.py](core.html): base request handler, for classes that function as a responder to HTTP requests
- **BaseModel**, in [model.py](model.html): base database model, which (by default) uses Guido van Rossum's new [NDB](http://code.google.com/p/appengine-ndb-experiment)
- **BasePipeline**, in [pipelines.py](pipeline.html): base pipeline class, with XMPP & channel logging and more useful shortcuts, for use with the [Pipelines](http://code.google.com/appengine-pipelines) library
- **BaseService**, in [services.py](services.html): base remote service class, with a suite of handy decorators for easily annotating remote methods with caching, security & audit policy
'''

from apptools.core import BaseHandler		 # BaseHandler for request dispatching, with API shortcuts and sessions and much more
from apptools.model import BaseModel         # BaseModel for data modelling, with serialization tools and much more (powered by NDB by default)
from apptools.services import BaseService    # BaseService for simple RPC services, integrated with ProtoRPC
from apptools.pipelines import BasePipeline  # BasePipeline for easy backend processing

## Getting started


# To **get started**, begin by extending BaseHandler:
class MyHandler(BaseHandler):

    def get(self):
        context = {
            'message': 'hello world!'
        }
        key = self.api.memcache.get('<somekey>')      # easy access to AppEngine APIs
        key = self.ext.ndb.key.Key(urlsafe=key)	      # easy access to NDB, Map/Reduce and Pipelines
        self.render('<sampletemplate>', **context)    # built-in jinja2 integration, with an awesome global context
