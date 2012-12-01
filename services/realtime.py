# -*- coding: utf-8 -*-

'''

Services: Realtime

Contains tools, classes, etc to dispatch services in a realtime environment, like WebSockets.

-sam (<sam@momentum.io>)

'''

from apptools import util

from protorpc import remote
from protorpc import transport


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
		pass

	@staticmethod
	def decode_message(message_type, encoded_message):
		pass


	def send_rpc(self, remote_info, request):
		pass