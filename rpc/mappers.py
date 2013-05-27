# -*- coding: utf-8 -*-

"""
--------------------------
apptools2: service mappers
--------------------------

protoRPC mappers enable the apptools service layer to speak
any language - they are responsible for serialization,
deserialization, and codec management. this package contains
default mappers that ship with apptools.

:author: Sam Gammon (sam@momentum.io)
:copyright: (c) 2013 momentum labs.
:license: This is private source code - Ampush has been granted an
          unlimited, exclusive license for embedded use. For details
          about embedded licenses and other legalese, see `LICENSE.md`.
"""

# stdlib
import hmac
import config
import base64
import hashlib
import webapp2
import datetime

# apptools rpc
from apptools import rpc

# protorpc
from protorpc import messages
from protorpc import protojson

# service handlers
from protorpc.webapp import service_handlers

# apptools util
from apptools import util
from apptools.util import debug


# Environment check: Google App Engine
try:
    from google import appengine; _APPENGINE = appengine
except:
    _APPENGINE = False


# Constants
logging = debug.AppToolsLogger('apptools.rpc.mappers')
date_time_types = (datetime.datetime, datetime.date, datetime.time)


##### +=+=+=+=+ Feed Format Support +=+=+=+=+ #####

## Custom RSS mapper - extends an internal ProtoRPC class so that we can properly manage API requests in RSS format.
#@rpc.mapper
class RSS(service_handlers.RPCMapper):

    ''' Custom RSS mapper for API request & response messages. '''

    pass


## Custom RSS mapper - extends an internal ProtoRPC class so that we can properly manage API requests in Atom format.
#@rpc.mapper
class ATOM(service_handlers.RPCMapper):

    ''' Custom Atom mapper for API request & response messages. '''

    pass


##### +=+=+=+=+ XMLRPC Format Support +=+=+=+=+ #####

## Custom XML mapper - extends an internal ProtoRPC class so that we can properly manage API requests in XML format.
#@rpc.mapper
class XMLRPC(service_handlers.RPCMapper):

    ''' Custom XML mapper for API request & response messages. '''

    pass


##### +=+=+=+=+ JSONRPC Format Support +=+=+=+=+ #####

## JSONRPC - custom RPC mapper that properly unpacks JSONRPC requests according to apptools' **wire format**.
@rpc.mapper
class JSONRPC(service_handlers.JSONRPCMapper, rpc.ConfiguredClass):

    ''' Custom JSONRPC Mapper for managing JSON API requests. '''

    _config_path = 'apptools.rpc.mappers.JSONRPC'

    handler = None
    _request = {

        'id': None,
        'opts': {},
        'agent': {}

    }

    http_methods = ('GET', 'POST', 'PUT', 'DELETE')
    content_types = ('application/json', 'application/x-json', 'application/json-rpc', 'apptools/json-rpc')

    class _MessageJSONEncoder(protojson.MessageJSONEncoder):

        ''' Custom JSON encoder for API request & response messages. '''

        indent = None
        encoding = 'utf-8'
        sort_keys = True
        allow_nan = True
        ensure_ascii = True
        check_circular = True
        skipkeys = True
        use_decimal = False

        current_indent_level = 0

        def __init__(self, *args, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

            self._MessageJSONEncoder__protojson_protocol = protojson.ProtoJson()

        def default(self, value):

            ''' Overrides JSONEncoder's default() method. '''

            if isinstance(value, messages.Enum):
                return str(value)

            if isinstance(value, messages.Message):
                result = {}
                for field in value.all_fields():
                    item = value.get_assigned_value(field.name)
                    if item not in (None, [], ()):
                        result[field.name] = self.jsonForValue(item)
                        if isinstance(item, list):  # for repeated values...
                            listvalue = [self.jsonForValue(x) for x in item]
                            result[field.name] = listvalue

                else:
                    return super(self.__class__, self).default(value)

            elif isinstance(value, JSONRPC.GenericResponse):
                result = {}
                for k, v in value.to_dict().items():
                    if v not in (None, [], ()):
                        if isinstance(v, list):
                            listvalue = [self.jsonForValue(x) for x in v]
                            result[k] = listvalue
                        else:
                            result[k] = self.jsonForValue(v)
                    else:
                        result[k] = super(self.__class__, self).default(v)
            else:
                return super(self.__class__, self).default(value)

            return result

        def jsonForValue(self, value):

            ''' Return JSON for a given Python value. '''

            if isinstance(value, (basestring, int, float, bool)):
                return value

            elif isinstance(value, date_time_types):
                return str(value)

            elif isinstance(value, messages.Message):
                for item in value.all_fields():
                    self.jsonForValue(item)

            else:
                return str(value)

    @webapp2.cached_property
    def ServicesConfig(self):

        ''' Return the project services config. '''

        if config:
            return config.config.get('apptools.project.services')
        return {'debug': True}

    def encode_request(self, struct):

        ''' Encode a request. '''

        encoded = self._MessageJSONEncoder().encode(struct)
        return encoded

    @classmethod
    def encode_message(cls, message):

        ''' Encode a message. '''

        return cls._MessageJSONEncoder().encode(message)

    @classmethod
    def decode_message(cls, response_type, content):

        ''' Decode a JSON-encoded blob into a Message. '''

        mapper = cls()

        interpreted = protojson._load_json_module().loads(content)
        full_response = mapper._decode_message(response_type, interpreted.get('response', {}).get('content', {}))
        return full_response

    def build_response(self, handler, response, response_envelope=None, extra_response_content={}):

        ''' Encode a response. '''

        self.handler = handler
        try:
            if isinstance(response, messages.Message):
                response.check_initialized()
            else:
                response = self.GenericResponse.from_struct(response)
            if response_envelope is not None and handler is None:
                envelope = self.envelope(response_envelope, response)
                if extra_response_content is not None and isinstance(extra_response_content, dict):
                    for k, v in extra_response_content.items():
                        if k not in envelope['response']:
                            envelope['response'][k] = v
                encoded_response = self._MessageJSONEncoder().encode(envelope)
                return encoded_response
            else:
                envelope = self._MessageJSONEncoder().encode(self.envelope(handler._response_envelope, response))

        except messages.ValidationError, err:
            raise service_handlers.RequestError('Unable to encode message: %s' % err)
        else:
            if handler is not None:  # so we can inject responses...
                handler.response.headers['Content-Type'] = "application/json"
                handler.response.write(envelope)
            return envelope

    def envelope(self, wrap, response):

        ''' Wrap the result of the request in a descriptive, helpful envelope. '''

        if config:
            sysconfig = config.config.get('apptools.project', {})
        else:
            sysconfig = {'debug': True}

        ## Compile signature
        signature = [
            self.ServicesConfig.get('config', {}).get('secret_key', '__development__'),  # HMAC key
            str(response),  # message
            self.ServicesConfig.get('config', {}).get('hmac_hash', hashlib.sha512)  # hash algorithm
        ]

        ## Start building response
        response_envelope = {

            'id': wrap.get('id'),
            'status': wrap.get('status'),
            'response': {},
            'flags': wrap.get('flags'),
            'platform': {
                'name': config.config.get('apptools.project', {}).get('name', 'AppTools'),
                'version': '.'.join(map(lambda x: str(x), [
                                    sysconfig.get('version', {}).get('major', 1),
                                    sysconfig.get('version', {}).get('minor', 0),
                                    sysconfig.get('version', {}).get('micro', 0)]))
            }

        }

        ## Add debug info
        if (config.debug or self.ServicesConfig.get('debug', False)) and _APPENGINE:
            response_envelope['platform']['debug'] = config.debug
            response_envelope['platform']['build'] = sysconfig.get('version', {}).get('build', 'RELEASE')
            response_envelope['platform']['release'] = sysconfig.get('version', {}).get('release', 'PRODUCITON')
            response_envelope['platform']['engine'] = 'AppTools/ProtoRPC'

            if self.ServicesConfig.get('debug', False):
                response_envelope['platform']['info'] = {

                    'datacenter': self.handler.request.environ.get('DATACENTER'),
                    'instance': self.handler.request.environ.get('INSTANCE_ID'),
                    'request_id': self.handler.request.environ.get('REQUEST_ID_HASH'),
                    'server': self.handler.request.environ.get('SERVER_SOFTWARE'),
                    'runtime': self.handler.request.environ.get('APPENGINE_RUNTIME'),
                    'multithread': self.handler.request.environ.get('wsgi.multithread'),
                    'multiprocess': self.handler.request.environ.get('wsgi.multiprocess')

                }
                if self.handler.api.backends.get_backend() is not None:
                    response_envelope['platform']['info']['layer'] = 'backend'
                    response_envelope['platform']['info']['instance'] = self.handler.api.backends.get_instance()
                else:
                    response_envelope['platform']['info']['layer'] = 'frontend'

        ## Add actual response
        response_envelope['response'] = {

            'type': str(response.__class__.__name__),
            'content': response,
            'signature': hmac.new(*signature).hexdigest()

        }

        ## Done!
        return response_envelope

    def _decode_message(self, message_type, dictionary):

        ''' Decode a Message. '''

        def decode_dictionary(message_type, dictionary):

            ''' Decode a dictionary of items (recursive). '''

            message = message_type()
            if isinstance(dictionary, dict):
                for key, value in dictionary.iteritems():
                    if value is None:
                        message.reset(key)
                        continue

                    try:
                        field = message.field_by_name(key)
                    except KeyError:
                        # TODO(rafek): Support saving unknown values.
                        continue

                    # Normalize values in to a list.
                    if isinstance(value, list):
                        if not value:
                            continue
                    else:
                        value = [value]

                    valid_value = []
                    for item in value:
                        if isinstance(field, messages.EnumField):
                            item = field.type(item)
                        elif isinstance(field, messages.BytesField):
                            item = base64.b64decode(item)
                        elif isinstance(field, messages.MessageField):
                            item = decode_dictionary(field.type, item)
                        elif (isinstance(field, messages.FloatField) and
                                isinstance(item, (int, long))):
                            item = float(item)
                        valid_value.append(item)

                    if field.repeated:
                        setattr(message, field.name, valid_value)
                    else:
                        setattr(message, field.name, valid_value[-1])
            return message

        message = message_type()
        if isinstance(dictionary, list):
            return message
        elif isinstance(dictionary, dict):
            for key, value in dictionary.iteritems():
                if value is None:
                    message.reset(key)
                    continue

                try:
                    field = message.field_by_name(key)
                except KeyError:
                    # TODO(rafek): Support saving unknown values.
                    continue

                # Normalize values in to a list.
                if isinstance(value, list):
                    if not value:
                        continue
                else:
                    value = [value]

                valid_value = []
                for item in value:
                    if isinstance(field, messages.EnumField):
                        item = field.type(item)
                    elif isinstance(field, messages.BytesField):
                        item = base64.b64decode(item)
                    elif isinstance(field, messages.MessageField):
                        item = decode_dictionary(field.type, item)
                    elif (isinstance(field, messages.FloatField) and
                            isinstance(item, (int, long))):
                        item = float(item)
                    valid_value.append(item)

                if field.repeated:
                    getattr(message, field.name)
                    setattr(message, field.name, valid_value)
                else:
                    setattr(message, field.name, valid_value[-1])

        return message

    def build_request(self, handler, request_type):

        ''' Build a request object. '''

        try:
            if hasattr(handler, 'interpreted_body') and handler.interpreted_body is not None:
                request_object = handler.interpreted_body
            else:
                request_object = protojson._load_json_module().loads(handler.request.body)

            request_body = request_object.get('request', request_object)
            handler._request_envelope['id'] = request_object.get('id', 1)
            handler._request_envelope['opts'] = request_object.get('opts', {})
            handler._request_envelope['agent'] = request_object.get('agent', {})

            if self.ServicesConfig.get('debug', False) is True:
                self.logging.info('Decoding message...')

            params = request_body.get('params', request_body)
            return self._decode_message(request_type, params)

        except (messages.ValidationError, messages.DecodeError), err:
            raise service_handlers.RequestError('Unable to parse request content: %s' % err)


##### +=+=+=+=+ Protobuf Format Support +=+=+=+=+ #####

## Protobuf - custom RPC mapper that properly manages Protobuf-format requests.
#@rpc.mapper
class Protobuf(service_handlers.ProtobufRPCMapper):

    ''' Custom Protobuf mapper for API request & response messages. '''

    pass


##### +=+=+=+=+ URLEncoded Form Support +=+=+=+=+ #####

## URLEncoded - custom RPC mapper that properly manages URLEncoded forms.
#@rpc.mapper
class URLEncoded(service_handlers.URLEncodedRPCMapper):

    ''' Custom URLEncoded form mapper for API request & response messages. '''

    pass


##### +=+=+=+=+ msgpack Support +=+=+=+=+ #####

## Msgpack - custom RPC mapper that properly manages URLEncoded forms.
#@rpc.mapper
class Msgpack(service_handlers.URLEncodedRPCMapper):

    ''' Custom URLEncoded form mapper for API request & response messages. '''

    pass
