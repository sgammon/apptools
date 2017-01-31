# -*- coding: utf-8 -*-

'''

    apptools model adapter: protoRPC

    allows apptools models to be inflated
    from and expressed as protorpc messages.

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


# stdlib
import datetime

# adapter API
from .abstract import KeyMixin
from .abstract import ModelMixin

# apptools util
from apptools.util import datastructures


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
        datetime.datetime: pmessages.StringField
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
        from apptools import rpc
        from apptools import model

        # provision field increment and message map
        _field_i, _model_message = 1, {'__module__': _model.__module__}

        # grab lookup and property dict
        lookup, property_map = _model.__lookup__, {}

        # add key submessage
        _model_message['key'] = pmessages.MessageField(rpc.Key, _field_i)

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
                _model_message[name] = rpc.VariantField(_field_i)
                continue

            # check recursive submodels
            elif isinstance(prop._basetype, type(type)) and issubclass(prop._basetype, model.AbstractModel):

                # shortcut: `model.Model` for `VariantField`s
                if prop._basetype is model.Model:

                    ## general, top-level `Model` means a variant field
                    _field_i = _field_i + 1
                    _model_message[name] = rpc.VariantField(_field_i)
                    continue

                # recurse - it's a model class
                _field_i = _field_i + 1
                _pargs.append(prop._basetype.to_message_model())
                _pargs.append(_field_i)

                # factory
                _model_message[name] = pmessages.MessageField(*_pargs, **_pkwargs)
                continue

            # check for keys (implemented with `basestring` for now)
            elif prop._basetype == model.Key:

                # build field and advance
                _field_i = _field_i + 1
                _pargs.append(rpc.Key)
                _pargs.append(_field_i)
                _model_message[name] = pmessages.MessageField(*_pargs)
                continue

            elif isinstance(prop._basetype, type) and issubclass(prop._basetype, datastructures.BidirectionalEnum):

                # quick check: empty enums create stringfields
                if not len(prop._basetype.__forward__):
                    _field_i = _field_i + 1
                    _pargs.append(_field_i)
                    _model_message[name] = pmessages.StringField(*_pargs, **_pkwargs)
                    continue

                # pop first data item off and check type
                if isinstance(getattr(prop._basetype, prop._basetype.__forward__[0]), basestring):

                    # for string values, simply use a string property...
                    _field_i = _field_i + 1
                    _pargs.append(_field_i)
                    _model_message[name] = pmessages.StringField(*_pargs, **_pkwargs)

                else:
                    # it's an enum-compatible class, dynamically build one
                    # ... build class internals
                    enum_klass = {
                        '__module__': prop._basetype.__module__
                    }

                    # otherwise, just add data properties
                    enum_klass.update(prop._basetype.__serialize__())

                    # construct enum class
                    enum = type(prop._basetype.__name__, (pmessages.Enum,), enum_klass)

                    # build field and advance
                    _field_i = _field_i + 1
                    _pargs.append(enum)
                    _pargs.append(_field_i)
                    _model_message[name] = pmessages.EnumField(*_pargs, **_pkwargs)
                    continue

            # check builtin basetypes
            elif prop._basetype in _builtin_basetypes:

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

    ## ProtoRPCKey
    # Mixin to core `Key` class that enables ProtoRPC message conversion.
    class ProtoRPCKey(KeyMixin):

        ''' Adapt `Key` classes to ProtoRPC messages. '''

        def to_message(self):

            ''' Convert a `Key` instance to a ProtoRPC `Message` instance.

                :returns: Constructed :py:class:`protorpc.Key` message object. '''

            from apptools import rpc
            return rpc.Key(id=str(self.id), kind=self.kind, encoded=self.urlsafe())

        @classmethod
        def to_message_model(cls):

            ''' Return a schema for a `Key` instance in ProtoRPC `Message` form.

                :returns: Vanilla :py:class:`protorpc.Key` class. '''

            from apptools import rpc
            return rpc.Key

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
            from apptools import rpc
            from apptools import model

            values = {}
            for prop, value in self.to_dict(*args, **kwargs).items():

                # convert keys => urlsafe
                if isinstance(value, model.Key):
                    values[prop] = rpc.Key(id=value.id, kind=value.kind, encoded=value.urlsafe())
                    continue

                # convert date/time/datetime => string
                if isinstance(value, (datetime.date, datetime.time, datetime.datetime)):
                    values[prop] = value.isoformat()
                    continue

                values[prop] = value  # otherwise, just set it

            if self.key:
                return self.__class__.to_message_model()(key=self.key.to_message(), **values)

            def _check_value(item):

                ''' Checks for invalid ProtoRPC values. '''

                key, value = item

                if isinstance(value, list) and len(value) == 0:
                    return False
                return True

            return self.__class__.to_message_model()(**dict(filter(_check_value, values.iteritems())))

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
