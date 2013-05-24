# -*- coding: utf-8 -*-

"""
-------------------------------------
apptools2: model adapter for protorpc
-------------------------------------

allows apptools models to be inflated
from and expressed as protorpc messages.

:author: Sam Gammon (sam@momentum.io)
:copyright: (c) 2013 momentum labs.
:license: This is private source code - Ampush has been granted an
          unlimited, exclusive license for embedded use. For details
          about embedded licenses and other legalese, see `LICENSE.md`.
"""

# stdlib
import datetime

# adapter API
from .abstract import KeyMixin
from .abstract import ModelMixin

# apptools util
from apptools.util import datastructures

# apptools datastructures
from apptools.util.datastructures import BidirectionalEnum


## == protorpc support == ##
try:
    # force absolute import to prevent infinite recursion
    protorpc = __import__('protorpc', tuple(), tuple(), [], -1)

except ImportError as e:  # pragma: no cover
    # flag as unavailable
    _PROTORPC, _root_message_class = False, object

else:
    # extended imports (must be absolute)
    pmessages = getattr(__import__('protorpc', tuple(), tuple(), ['messages'], -1), 'messages')
    pmessage_types = getattr(__import__('protorpc', tuple(), tuple(), ['message_types'], -1), 'message_types')

    # constants
    _model_impl = {}
    _field_kwarg = 'field'
    _PROTORPC, _root_message_class = True, pmessages.Message

    # map fields to basetypes
    _field_basetype_map = {
        int: pmessages.IntegerField,
        bool: pmessages.BooleanField,
        float: pmessages.FloatField,
        str: pmessages.StringField,
        unicode: pmessages.StringField,
        basestring: pmessages.StringField,
        datetime.time: pmessages.StringField,
        datetime.date: pmessages.StringField,
        datetime.datetime: pmessages.StringField,
        BidirectionalEnum: pmessages.EnumField
    }

    # build quick basetype lookup
    _builtin_basetypes = frozenset(_field_basetype_map.keys())

    # map fields to explicit names
    _field_explicit_map = {
        pmessages.EnumField.__name__: pmessages.EnumField,  # 'EnumField'
        pmessages.BytesField.__name__: pmessages.BytesField,  # 'BytesField'
        pmessages.FloatField.__name__: pmessages.FloatField,  # 'FloatField'
        pmessages.StringField.__name__: pmessages.StringField,  # 'StringField'
        pmessages.IntegerField.__name__: pmessages.IntegerField,  # 'IntegerField'
        pmessages.BooleanField.__name__: pmessages.BooleanField  # 'BooleanField'
    }

    # build quick builtin lookup
    _builtin_fields = frozenset(_field_explicit_map.keys())

    # recursive message builder
    def build_message(_model):

        ''' Recursively builds a new `Message` class dynamically from an apptools
            :py:class:`model.Model`. Properties are converted to their :py:mod:`protorpc`
            equivalents and factoried into a full :py:class:`messages.Message` class.

            :param _model: Model class to convert to a :py:class:`protorpc.messages.Message`.
            :raises TypeError: In the case of an unidentified or unknown property basetype.
            :raises ValueError: In the case of a missing implementation field or serialization error.
            :returns: Constructed (but not instantiated) :py:class:`protorpc.messages.Message` class. '''

        # must nest import to avoid circular dependencies
        from apptools import model
        from apptools import services

        # provision field increment and message map
        _field_i, _model_message = 1, {'__module__': _model.__module__}

        # grab lookup and property dict
        lookup, property_map = _model.__lookup__, {}

        # add key submessage
        _model_message['key'] = pmessages.MessageField(Key, _field_i)

        # build fields from model properties
        for name in lookup:

            # init args and kwargs
            _pargs, _pkwargs = [], {}

            # grab property class
            prop = property_map[name] = _model.__dict__[name]

            # copy in default if field has explicit default value
            if prop._default != prop._sentinel:
                _pkwargs['default'] = prop._default

            # map in required and repeated kwargs
            _pkwargs['required'], _pkwargs['repeated'] = prop._required, prop._repeated

            # check for explicit field
            if _field_kwarg in prop._options:

                # grab explicit field, if any
                explicit = prop._options.get(_field_kwarg, datastructures._EMPTY)

                # explcitly setting `False` or `None` means skip this field
                if (explicit is False or explicit is None) and explicit != datastructures._EMPTY:
                    continue  # continue without incrementing: skipped field

                # if it's a tuple, it's a name/args/kwargs pattern
                if not isinstance(explicit, (basestring, tuple)):
                    context = (name, _model.kind(), type(explicit))
                    raise TypeError('Invalid type found for explicit message field implementation binding - property'
                                    '\"%s\" of model \"%s\" cannot bind to field of type \"%s\". A basestring field'
                                    'name or tuple of (name, *args, <**kwargs>) was expected.' % context)

                elif isinstance(explicit, tuple):

                    # two indicates name + args
                    if len(explicit) == 2:  # name, *args
                        explicit, _pargs = explicit
                        _pkwargs = {}

                    # three indicates name + args + kwargs
                    elif len(explicit) == 3:  # name, *args, **kwargs
                        explicit, _pargs, _pkwargs = explicit

                # grab explicit field (if it's not a tuple it's a basestring)
                if explicit in _builtin_fields:

                    # flatten arguments, splice in ID
                    if len(_pargs) > 0:
                        if not isinstance(_pargs, list):
                            _pargs = [i for i in _pargs]

                        _field_i = _field_i + 1
                        _pargs.append(_field_i)
                        _pargs = tuple(_pargs)
                    else:
                        # shortcut: replace it if there's no args
                        _field_i = _field_i + 1
                        _pargs = (_field_i,)

                    # factory field
                    _model_message[name] = _field_explicit_map[explicit](*_pargs, **_pkwargs)
                    continue

                else:
                    # raise a `ValueError` in the case of an invalid explicit field name
                    raise ValueError("No such message implementation field: \"%s\"." % name)

            # check variant by dict
            if prop._basetype == dict:
                _field_i = _field_i + 1
                _model_message[name] = services.VariantField(_field_i)
                continue

            # check recursive submodels
            if isinstance(prop._basetype, type(type)) and issubclass(prop._basetype, model.AbstractModel):

                # shorcut: `model.Model` for `VariantField`s
                if prop._basetype is model.Model:

                    ## general, top-level `Model` means a variant field
                    _field_i = _field_i + 1
                    _model_message[name] = services.VariantField(_field_i)
                    continue

                # recurse - it's a model class
                _field_i = _field_i + 1
                _pargs.append(prop._basetype.to_message_model())
                _pargs.append(_field_i)

                # factory
                _model_message[name] = pmessages.MessageField(*_pargs)
                continue

            # check for keys (implemented with `basestring` for now)
            if prop._basetype == model.Key:

                # build field and advance
                _field_i = _field_i + 1
                _pargs.append(Key)
                _pargs.append(_field_i)
                _model_message[name] = pmessages.MessageField(*_pargs)
                continue

            # check builtin basetypes
            if prop._basetype in _builtin_basetypes:

                # build field and advance
                _field_i = _field_i + 1
                _pargs.append(_field_i)
                _model_message[name] = _field_basetype_map[prop._basetype](*_pargs, **_pkwargs)
                continue

            # check for builtin hook for message implementation
            elif hasattr(prop._basetype, '__message__'):

                # delegate field and advance
                _field_i = _field_i + 1
                _pargs.append(_field_i)
                _model_message[name] = prop._basetype.__message__(*_pargs, **_pkwargs)
                continue

            else:
                context = (name, _model.kind(), prop._basetype)
                raise ValueError("Could not resolve proper serialization for property \"%s\""
                                 "of model \"%s\" (found basetype \"%s\")." % context)

        # construct message class on-the-fly
        return type(_model.kind(), (pmessages.Message,), _model_message)

    ## Key
    # Expresses a `model.Key` as a message.
    class Key(pmessages.Message):

        ''' Message that expresses a `model.Key`. '''

        id = pmessages.StringField(1)
        kind = pmessages.StringField(2)
        encoded = pmessages.StringField(3)

    ## ProtoRPCKey
    # Mixin to core `Key` class that enables ProtoRPC message conversion.
    class ProtoRPCKey(KeyMixin):

        ''' Adapt `Key` classes to ProtoRPC messages. '''

        def to_message(self):

            ''' Convert a `Key` instance to a ProtoRPC `Message` instance.

                :returns: Constructed :py:class:`protorpc.Key` message object. '''

            return Key(id=str(self.id), kind=self.kind, encoded=self.urlsafe())

    ## ProtoRPCModel
    # Mixin to core `Model` class that enables ProtoRPC message conversion.
    class ProtoRPCModel(ModelMixin):

        ''' Adapt Model classes to ProtoRPC messages. '''

        def to_message(self, *args, **kwargs):

            ''' Convert a `Model` instance to a ProtoRPC `Message` class.

                :param args: Positional arguments to pass to :py:meth:`Model.to_dict`.
                :param kwargs: Keyword arguments to pass to :py:meth:`Model.to_dict`.
                :returns: Constructed and initialized :py:class:`protorpc.Message` object. '''

            # must import inline to avoid circular dependency
            from apptools import model

            if self.key:
                return self.__class__.to_message_model()(key=self.key.to_message(),
                                                         **self.to_dict(*args, **kwargs))

            values = {}
            for bundle in self.to_dict(*args, **kwargs):
                prop, value = bundle

                # covert datetime types => isoformat
                if isinstance(value, (datetime.time, datetime.date, datetime.datetime)):
                    values[prop] = value.isoformat()
                    continue

                # convert keys => urlsafe
                if isinstance(value, model.Key):
                    values[prop] = Key(id=value.id, kind=value.kind, encoded=value.urlsafe())
                    continue

                values[prop] = value  # otherwise, just set it

            return self.__class__.to_message_model()(**values)

        @classmethod
        def to_message_model(cls):

            ''' Convert a `Model` class to a ProtoRPC `Message` class. Delegates
                to :py:func:`build_message`, see docs there for exceptions raised
                (:py:exc:`TypeError` and :py:exc:`ValueError`).

                :returns: Constructed (but not initialized) dynamically-build
                          :py:class:`message.Message` class corresponding to
                          the current model (``cls``). '''

            global _model_impl

            # check global model=>message implementation cache
            if (cls, cls.__lookup__) not in _model_impl:

                # build message class
                _model_impl[(cls, cls.__lookup__)] = build_message(cls)

            # return from cache
            return _model_impl[(cls, cls.__lookup__)]
