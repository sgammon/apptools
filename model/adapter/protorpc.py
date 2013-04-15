# -*- coding: utf-8 -*-

'''

    apptools2: model adapter for protorpc
    -------------------------------------------------
    |                                               |
    |   `apptools.model.adapter.protorpc`           |
    |                                               |
    |   allows apptools models to be inflated       |
    |   from and expressed as protorpc messages.    |
    |                                               |
    -------------------------------------------------
    |   authors:                                    |
    |       -- sam gammon (sam@momentum.io)         |
    -------------------------------------------------
    |   changelog:                                  |
    |       -- apr 1, 2013: initial draft           |
    -------------------------------------------------

'''

# adapter API
from .abstract import ModelAdapter


## == protorpc support == ##
try:
    import protorpc
    from protorpc import messages as pmessages
    from protorpc import message_types as pmessage_types

except ImportError as e:
    # flag as unavailable
    _PROTORPC, _root_message_class = False, object

else:
    # flag as available
    _PROTORPC, _root_message_class = True, pmessages.Message


## ProtoRPCAdapter
# Adapt apptools models to ProtoRPC messages.
class ProtoRPCAdapter(ModelAdapter):

    ''' Adapt model classes to ProtoRPC. '''

    @classmethod
    def is_supported(cls):

        ''' Check whether this adapter is supported in the current environment. '''

        return False
