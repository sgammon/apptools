# -*- coding: utf-8 -*-

'''

Services: Realtime

Contains tools, classes, etc to dispatch services in a realtime environment, like WebSockets.

-sam (<sam@momentum.io>)

'''

# Base Imports
import abc
import config

# AppTools Imports
from apptools import util

# ProtoRPC Imports
from protorpc import remote
from protorpc import transport


## RealtimeProtocol - abstract base class for extension into a spec'd realtime protocol
class RealtimeProtocol(object):

	''' Describes a protocol for realtime communications. '''

	__metaclass__ = abc.ABCMeta

	@classmethod
	def pack(cls, struct):

		''' Serialize and encode a structure. '''

		return cls.encode(cls.serialize(struct))

	@classmethod
	def unpack(cls, raw, kind=None):

		''' Decode and deserialize a raw frame. '''

		return cls.deserialize(cls.decode(raw))

	@util.decorators.classproperty
	def config(cls):

		''' Named config pip for all RealtimeProtocol(s). '''

		if hasattr(cls, 'config_path'):
			return config.config.get('.'.join(['apptools.realtime.protocol', cls.__name__]), {})
		else:
			return config.config.get(cls.config_path, config.config.get('.'.join(['apptools.realtime.protocol', cls.__name__])))

	@util.decorators.classproperty
	def logging(cls):

		''' Named logging pipe for all RealtimeProtocol(s). '''

		return util.debug.AppToolsLogger(path='apptools.realtime.protocol', name=cls.__name__)._setcondition(self.config.get('debug', config.debug))

	@abc.abstractproperty
	def name(self): pass

	@abc.abstractproperty
	def commands(self): pass

	@abc.abstractproperty
	def vocabulary(self): pass

	@abc.abstractproperty
	def errocodes(self): pass

	@abc.abstractmethod
	def encode(self, struct): pass

	@abc.abstractmethod
	def decode(self, data): pass

	@abc.abstractproperty
	def encoder(self): pass

	@abc.abstractproperty
	def decoder(self): pass

	@abc.abstractmethod
	def serialize(self, message): pass

	@abc.abstractmethod
	def deserialize(self, frame): pass

	@abc.abstractmethod
	def error(self, code): pass


## RealtimeRPCState - replacement for proto's RpcState class, suitable for realtime services
class RealtimeRPCState(remote.RpcState):

	''' Keeps state about the current RPC lifecycle. '''


## RealtimeRequestState - replacement for proto's HttpRequestState class, suitable for realtime services
class RealtimeRequestState(remote.RequestState):

	''' Adapts internal ProtoRPC request state structures to allow realtime dispatching. '''

	agent = None
	clientlib = None
	remote_host = None
	remote_address = None
	server_host = None
	server_port = None
	service_path = None
	protocol = 'realtime'

	def __init__(self, **kwargs):

		''' Map keyword args into state. '''

		for k, v in kwargs:
			setattr(self, k, v)


## SocketTransport - protocol and transport mechanism for bridging sockets/realtime data and services
class SocketTransport(transport.Transport):

	''' Allows ProtoRPC requests to travel and properly be decoded/encoded over a WebSocket. '''

	protocol = None

	@staticmethod
	def encode_message(message):

		''' Encode a response payload. '''

		return self.protocol.pack(message)

	@staticmethod
	def decode_message(message_type, message):

		''' Decode a request payload. '''

		return self.protocol.unpack(message, kind=message_type)

	def send_rpc(self, remote_info, request):

		''' Send an RPC over a socket. '''

		raise NotImplemented()
