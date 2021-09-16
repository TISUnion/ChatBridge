import json
from socket import socket
from threading import Thread, RLock, Event
from typing import Dict, Optional

from chatbridge.core.client import ChatBridgeClient
from chatbridge.core.config import ClientInfo
from chatbridge.common import constants
from chatbridge.core.network import net_util
from chatbridge.core.network.basic import Address, ChatBridgeBase
from chatbridge.core.network.protocol import LoginPacket, ChatBridgePacket


class _ClientConnection(ChatBridgeClient):
	def __init__(self, holder: '_ClientHolder', conn: socket, address: Address, info: ClientInfo):
		self.info = info  # so get_logging_name() works
		super().__init__(holder.server.aes_key, address, ClientInfo(name=constants.SERVER_NAME, password=''))
		self._sock = conn
		self.holder = holder

	def get_logging_name(self) -> str:
		return 'Server.{}'.format(self.info.name)

	def _login(self):
		"""
		No need to login for this class
		"""
		pass

	def _on_packet(self, packet: ChatBridgePacket):
		super()._on_packet(packet)
		self.holder.server.transfer_packet(self, packet)

	def _on_started(self):
		super()._on_started()
		self.logger.info('Started client connection')

	def _on_stopped(self):
		self.holder.on_connection_stopped()
		self.logger.info('Stopped client connection')
		super()._on_stopped()


class _ClientHolder:
	def __init__(self, server: 'ChatBridgeServer', info: ClientInfo):
		self.server = server
		self.info: ClientInfo = info
		self.connection: Optional[_ClientConnection] = None
		self.__lock = RLock()

	def is_online(self) -> bool:
		with self.__lock:
			return self.connection is not None and self.connection.is_online()

	def start(self, conn: socket, addr: Address):
		self.stop()
		with self.__lock:
			self.connection = _ClientConnection(self, conn, addr, self.info)
			self.connection.start()

	def stop(self):
		with self.__lock:
			if self.connection is not None:
				self.connection.stop()

	def get_ping_text(self) -> str:
		with self.__lock:
			if self.connection is not None:
				return '{}ms'.format(round(self.connection.ping * 1000, 2))
			else:
				return 'N/A'

	def on_connection_stopped(self):
		with self.__lock:
			self.connection = None

	def send_packet(self, packet: ChatBridgePacket):
		connection = self.connection
		if connection is not None:
			connection.send_packet(packet)


class ChatBridgeServer(ChatBridgeBase):
	def __init__(self, aes_key: str, server_address: Address):
		super().__init__('Server', aes_key)
		self.server_address = server_address
		self.clients: Dict[str, _ClientHolder] = {}
		self.__sock: Optional[socket] = None
		self.__thread_run: Optional[Thread] = None

	def add_client(self, client_info: ClientInfo):
		self.clients[client_info.name] = _ClientHolder(self, client_info)

	def _main_loop(self):
		self.__sock = socket()
		try:
			self.__sock.bind(self.server_address)
		except:
			self.logger.exception('Failed to bind {}'.format(self.server_address))
			return
		self.__sock.listen(5)
		self.logger.info('Server Started')
		try:
			while not self._is_stopping():
				try:
					conn, addr = self.__sock.accept()
					address = Address(*addr)
					self.logger.info('New connection from {}'.format(address.pretty_str()))
					self.__handle_connection(conn, address)
				except:
					if not self._is_stopping():
						self.logger.exception('Error ticking server')
		finally:
			self.stop()

	def stop(self):
		self._stopping_flag = True
		self.__sock.close()
		super().stop()

	def __handle_connection(self, conn: socket, addr: Address):
		success = False
		try:
			recv_str = net_util.receive_data(conn, self._cryptor, timeout=15)
			login_packet = LoginPacket.deserialize(json.loads(recv_str))
		except Exception as e:
			self.logger.error('Failed reading client\'s login packet: {}'.format(e))
			return
		else:
			client = self.clients.get(login_packet.name, None)
			if client is not None:
				if client.info.password == login_packet.password:
					success = True
					self.logger.info('Starting client {}'.format(client.info.name))
					client.start(conn, addr)
				else:
					self.logger.warning('Wrong password during login for client {}: expected {} but received {}'.format(client.info.name, client.info.password, login_packet.password))
			else:
				self.logger.warning('Unknown client name during login: {}'.format(login_packet.name))
		if not success:
			conn.close()
			self.logger.warning('Closed connection from {}'.format(addr.pretty_str()))

	def transfer_packet(self, client: _ClientConnection, packet: ChatBridgePacket):
		if packet.sender != client.info.name:
			self.logger.warning('Un-matched sender name during packet transferring, expected {} but found {}'.format(client.info.name, packet.sender))
			return
		self.logger.info('[{} -> {}] {}: {}'.format(
			packet.sender, ','.join(packet.receivers) if not packet.broadcast else '*',
			packet.type,
			packet.content
		))
		receivers = packet.receivers if not packet.broadcast else self.clients.keys()
		for receiver_name in set(receivers):
			if receiver_name != packet.sender:
				if receiver_name == constants.SERVER_NAME:
					self.on_packet(packet)
				elif receiver_name in self.clients:
					self.clients[receiver_name].send_packet(packet)
				else:
					self.logger.warning('Unknown client name {}'.format(receiver_name))

	def on_packet(self, packet: ChatBridgePacket):
		pass
