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
from .abstract import KeyMixin
from .abstract import ModelMixin


## == protorpc support == ##
try:
    # force absolute import to prevent infinite recursion
	protorpc = __import__('protorpc', tuple(), tuple(), [], -1)

except ImportError as e:
	# flag as unavailable
	_PROTORPC, _root_message_class = False, object

else:
    # extended imports (must be absolute)
    pmessages = getattr(__import__('protorpc', tuple(), tuple(), ['messages'], -1), 'messages')
    pmessage_types = getattr(__import__('protorpc', tuple(), tuple(), ['message_types'], -1), 'message_types')

    # flag as available
    _PROTORPC, _root_message_class = True, pmessages.Message

    ## ProtoRPCKey
    # Mixin to core `Key` class that enables ProtoRPC message conversion.
    class ProtoRPCKey(KeyMixin):

        ''' Adapt `Key` classes to ProtoRPC messages. '''

        def to_message(self, *args, **kwargs):

            ''' Convert a `Key` instance to a ProtoRPC `Message` instance. '''

            import pdb; pdb.set_trace()
            return False

        @classmethod
        def to_message_model(cls, *args, **kwargs):

            ''' Convert a `Key` class to a ProtoRPC `Message` class. '''

            import pdb; pdb.set_trace()
            return False


    ## ProtoRPCModel
    # Mixin to core `Model` class that enables ProtoRPC message conversion.
    class ProtoRPCModel(ModelMixin):

        ''' Adapt Model classes to ProtoRPC messages. '''

        def to_message(self, *args, **kwargs):

            ''' Convert a `Model` instance to a ProtoRPC `Message` class. '''

            import pdb; pdb.set_trace()
            message_properties = {}

            ## populate key, if any
            if self.key:
                pass  # @TODO: pass key over

            with self:
                for k, v in self.to_dict(*args, **kwargs):
                    pass  # @TODO: convert to protorpc fields
            return False

        @classmethod
        def to_message_model(cls, *args, **kwargs):

            ''' Convert a `Model` to a ProtoRPC `Message`. '''

            import pdb; pdb.set_trace()
            return False
