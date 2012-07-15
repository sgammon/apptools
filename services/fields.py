# -*- coding: utf-8 -*-

'''

Services: Fields

Contains useful ProtoRPC MessageField classes that can be used as properties in an RPC
request or response message.

-sam (<sam@momentum.io>)

'''

from protorpc import messages
from protorpc.messages import Field
from protorpc.messages import Variant


## VariantField
# A hack that allows a fully-variant field in ProtoRPC message classes.
class VariantField(Field):

    ''' Field definition for a completely variant field. '''

    VARIANTS = frozenset([Variant.DOUBLE, Variant.FLOAT, Variant.BOOL,
                          Variant.INT64, Variant.UINT64, Variant.SINT64,
                          Variant.INT32, Variant.UINT32, Variant.SINT32,
                          Variant.STRING, Variant.MESSAGE, Variant.BYTES, Variant.ENUM])

    DEFAULT_VARIANT = Variant.STRING

    type = (int, long, bool, basestring, dict, messages.Message)
