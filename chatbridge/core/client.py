import json
import random
import socket
import time
from enum import Enum, auto
from socket import timeout
from threading import Event, RLock
from threading import Thread
from typing import Optional, Iterable, Callable, Any, Union, Collection, TypeVar, Type

from mcdreforged.utils.serializer import Serializable

from chatbridge.common import constants
from chatbridge.core.config import ClientInfo, ClientConfig
from chatbridge.core.network import net_util
from chatbridge.core.network.basic import ChatBridgeBase, Address
from chatbridge.core.network.protocol import ChatBridgePacket, PacketType, AbstractPacket, ChatPayload, \
	KeepAlivePayload, AbstractPayload, CommandPayload, CustomPayload, DiscordChatPayload
from chatbridge.core.network.protocol import LoginPacket, LoginResultPacket


class ClientStatus(Enum):
	STARTING = auto()  # thread started
	CONNECTING = auto()  # socket connecting
	CONNECTED = auto()  # socket connected, logging in
	ONLINE = auto()   # logged in, thread started
	DISCONNECTED = auto()  # socket disconnected, cleaning threads
	STOPPED = auto()  # stopped


class ChatBridgeClient(ChatBridgeBase):
	KEEP_ALIVE_INTERVAL = 60
	KEEP_ALIVE_TIMEOUT = 15
	_PACKET_CALLBACK = Callable[[dict], Any]
	TIMEOUT = 10

	def __init__(self, aes_key: str, info: ClientInfo, *, server_address: Optional[Address] = None):
		super().__init__(info.name, aes_key)
		self.__server_address: Optional[Address] = server_address
		self.__sock: Optional[socket.socket] = None
		self.__sock_lock = RLock()
		self.__start_stop_lock = RLock()
		self.__status = ClientStatus.STOPPED
		self.__status_lock = RLock()
		self.__connection_done = Event()
		self.__keep_alive_received = Event()
		self.__ping_array = []
		self.__info = info
		self.__thread_keep_alive: Optional[Thread] = None

	@classmethod
	def create(cls, config: ClientConfig):
		return cls(config.aes_key, config.client_info, server_address=config.server_address)

	# --------------
	#     Status
	# --------------

	def _set_status(self, status: ClientStatus):
		with self.__status_lock:
			self.__status = status
		self.logger.debug('Client status set to {}'.format(status))

	def _in_status(self, status: Union[ClientStatus, Collection[ClientStatus]]):
		if isinstance(status, ClientStatus):
			status = (status,)
		with self.__status_lock:
			return self.__status in status

	def _assert_status(self, status: Union[ClientStatus, Collection[ClientStatus]]):
		if not self._in_status(status):
			raise AssertionError('Excepted status {} but {} found'.format(status, self.__status))

	def is_online(self) -> bool:
		return self._in_status(ClientStatus.ONLINE)

	def is_running(self) -> bool:
		return not self._is_stopped()

	def _is_connected(self) -> bool:
		return self._in_status({ClientStatus.CONNECTED, ClientStatus.ONLINE})

	def _is_stopping_or_stopped(self) -> bool:
		return self._in_status({ClientStatus.DISCONNECTED, ClientStatus.STOPPED})

	def _is_stopped(self) -> bool:
		return self._in_status(ClientStatus.STOPPED)

	# --------------
	#   Connection
	# --------------

	def set_server_address(self, addr: Address):
		self.__server_address = addr

	def get_server_address(self) -> Address:
		return self.__server_address

	@property
	def ping(self) -> float:
		"""
		ping in second
		"""
		return -1 if len(self.__ping_array) == 0 else sum(self.__ping_array) / len(self.__ping_array)

	def get_ping_text(self) -> str:
		if self.ping >= 0:
			return '{}ms'.format(round(self.ping * 1000, 2))
		else:
			return 'N/A'

	def _set_socket(self, sock: Optional[socket.socket]):
		with self.__sock_lock:
			self.__sock = sock

	def __connect(self):
		"""
		status: STOPPED -> CONNECTED
		"""
		self._assert_status(ClientStatus.STARTING)
		self._set_status(ClientStatus.CONNECTING)
		assert self.__server_address is not None
		self.logger.info('Connecting to {}'.format(self.__server_address))
		sock = socket.socket()
		sock.connect(self.__server_address)
		self._set_socket(sock)
		self._set_status(ClientStatus.CONNECTED)

	def __disconnect(self):
		"""
		status: STOPPED -> STOPPED, other -> DISCONNECTED
		"""
		if self._is_stopped():
			return
		with self.__sock_lock:
			self._set_status(ClientStatus.DISCONNECTED)  # set the status first so no exception errors get spammed
			if self.__sock is not None:
				try:
					self.__sock.close()
				except:
					pass
			self._set_socket(None)

	def _tick_connection(self):
		try:
			# self.logger.debug('Waiting for data received')
			packet = self._receive_packet(ChatBridgePacket)
		except timeout:
			# self.logger.debug('Timeout, ignore')
			pass
		else:
			self.logger.debug('Received packet with type {}: {}'.format(packet.type, packet.payload))
			try:
				self._on_packet(packet)
			except:
				self.logger.exception('Fail to process packet {}'.format(packet))

	# --------------
	#   Main Logic
	# --------------

	def start(self):
		self.logger.debug('Starting client')
		with self.__start_stop_lock:
			if self.is_running():
				self.logger.warning('Client is running, cannot start again')
				return
			self._set_status(ClientStatus.STARTING)
		self.__connection_done.clear()
		super().start()
		self.__connection_done.wait()
		self.logger.debug('Started client')

	def stop(self):
		self.logger.debug('Stopping client')
		with self.__start_stop_lock:
			if self._is_stopped():
				self.logger.warning('Client is stopped, cannot stop again')
				return
			self.__disconnect()  # state -> STOPPED or DISCONNECTED
		super().stop()
		self.logger.debug('Stopped client')

	def restart(self):
		self.logger.info('Restarting client')
		with self.__start_stop_lock:
			if not self._is_stopped():
				self.stop()
			self.start()

	def _connect_and_login(self):
		self.__connect()
		self._send_packet(LoginPacket(name=self.__info.name, password=self.__info.password))
		self._receive_packet(LoginResultPacket)
		self.logger.info('Connected to the server')

	def _main_loop(self):
		try:
			self._connect_and_login()
			self._set_status(ClientStatus.ONLINE)
		except Exception as e:
			(self.logger.exception if self.logger.is_debug_enabled() else self.logger.error)('Failed to connect to {}: {}'.format(self.__server_address, e))
			self.__disconnect()
			self.__connection_done.set()
		else:
			self._on_started()
			while self.is_online():
				try:
					self._tick_connection()
				except (ConnectionResetError, net_util.EmptyContent) as e:
					self.logger.warning('Connection closed: {}'.format(e))
					break
				except socket.error:
					if not self._is_stopping_or_stopped():
						self.logger.exception('Failed to receive data, stopping client now')
					break
				except:
					if not self._is_stopping_or_stopped():  # might already been handled and disconnected
						self.logger.exception('Error ticking client connection')
					break
			self._on_stopped()
		finally:
			self._set_status(ClientStatus.STOPPED)

	def _on_started(self):
		self.__connection_done.set()
		self.__thread_keep_alive = self._start_keep_alive_thread()
		self.__ping_array.clear()

	def _on_stopped(self):
		if self._is_connected():
			self.__disconnect()
		self.logger.debug('Joining keep alive thread')
		self.__thread_keep_alive.join()
		self.logger.debug('Joined keep alive thread')

	# ---------------------
	#   Packet core logic
	# ---------------------

	def _send_packet(self, packet: AbstractPacket):
		if self._is_connected():
			net_util.send_data(self.__sock, self._cryptor, packet)
		else:
			self.logger.warning('Trying to send a packet when not connected')

	T = TypeVar('T')

	def _receive_packet(self, packet_type: Type[T]) -> T:
		data_string = net_util.receive_data(self.__sock, self._cryptor, timeout=self.TIMEOUT)
		try:
			js_dict = json.loads(data_string)
		except ValueError:
			self.logger.exception('Fail to decode received string: {}'.format(data_string))
			raise
		if packet_type is dict:
			return js_dict
		try:
			packet = packet_type.deserialize(js_dict)
		except Exception:
			self.logger.exception('Fail to deserialize received json to {}: {}'.format(packet_type, js_dict))
			raise
		return packet

	def __build_and_send_packet(self, type_: str, receiver: Iterable[str], payload: AbstractPayload, *, is_broadcast: bool):
		self._send_packet(ChatBridgePacket(
			sender=self.get_name(),
			receivers=list(receiver),
			broadcast=is_broadcast,
			type=type_,
			payload=payload.serialize()
		))

	def send_to(self, type_: str, clients: Union[str, Iterable[str]], payload: AbstractPayload):
		if isinstance(clients, str):
			clients = (clients,)
		return self.__build_and_send_packet(type_, clients, payload, is_broadcast=False)

	def send_to_all(self, type_: str, payload: AbstractPayload):
		self.__build_and_send_packet(type_, [], payload, is_broadcast=True)

	# -------------------------
	#      Packet handlers
	# -------------------------

	def _on_packet(self, packet: ChatBridgePacket):
		"""
		A dispatcher that dispatch the packet based on packet type
		"""
		if packet.type == PacketType.keep_alive:
			self._on_keep_alive(packet.sender, KeepAlivePayload.deserialize(packet.payload))
		elif packet.type == PacketType.chat:
			self.on_chat(packet.sender, ChatPayload.deserialize(packet.payload))
		elif packet.type == PacketType.discord_chat:
			self.on_discord_chat(packet.sender, DiscordChatPayload.deserialize(packet.payload))
		elif packet.type == PacketType.command:
			self.on_command(packet.sender, CommandPayload.deserialize(packet.payload))
		elif packet.type == PacketType.custom:
			self.on_custom(packet.sender, CustomPayload.deserialize(packet.payload))

	def _on_keep_alive(self, sender: str, payload: KeepAlivePayload):
		if payload.is_ping():
			self.send_to(PacketType.keep_alive, sender, KeepAlivePayload.pong())
		elif payload.is_pong():
			self.__keep_alive_received.set()
		else:
			self.logger.warning('Unknown keep alive type: {}'.format(payload.ping_type))

	def on_chat(self, sender: str, payload: ChatPayload):
		pass

	def on_discord_chat(self, sender: str, payload: DiscordChatPayload):
		pass

	def on_command(self, sender: str, payload: CommandPayload):
		pass

	def on_custom(self, sender: str, payload: CustomPayload):
		pass

	# -------------------------
	#   Send packet shortcuts
	# -------------------------

	def _send_keep_alive_ping(self):
		self.send_to(PacketType.keep_alive, self._keep_alive_target(), KeepAlivePayload.ping())

	def send_chat(self, target: str, message: str, author: str = ''):
		self.send_to(PacketType.chat, target, ChatPayload(author=author, message=message))

	def broadcast_chat(self, message: str, author: str = ''):
		self.send_to_all(PacketType.chat, ChatPayload(author=author, message=message))

	def braodcast_discord_chat(self, role: str, color: str, author: str, message: str, 
					reply_name: str, reply_color: str, reply_mes: str):
		self.send_to_all(PacketType.discord_chat, DiscordChatPayload(
			role=role, color=color, author=author, message=message,
			reply_name=reply_name, reply_color=reply_color, reply_mes=reply_mes))

	def send_command(self, target: str, command: str, params: Optional[Union[Serializable, dict]] = None):
		self.send_to(PacketType.command, target, CommandPayload.ask(command, params))

	def reply_command(self, target: str, asker_payload: 'CommandPayload', result: Union[Serializable, dict]):
		self.send_to(PacketType.command, target, CommandPayload.answer(asker_payload, result))

	def send_custom(self, target: str, data: dict):
		self.send_to(PacketType.chat, target, CustomPayload(data=data))

	def broadcast_custom(self, data: dict):
		self.send_to_all(PacketType.chat, CustomPayload(data=data))

	# -------------------
	#   Keep Alive Impl
	# -------------------

	def _get_keep_alive_thread_name(self):
		return 'KeepAlive'

	def _start_keep_alive_thread(self) -> Thread:
		return self._start_thread(self._keep_alive_loop, self._get_keep_alive_thread_name())

	def _keep_alive_target(self) -> str:
		return constants.SERVER_NAME

	def _keep_alive_loop(self):
		"""
		Except to have the same life-span as the connection
		"""
		while self.is_online():
			time.sleep(random.random())
			if not self.is_online():
				break
			self.__keep_alive_received.clear()
			time_sent = time.monotonic()
			try:
				self._send_keep_alive_ping()
			except:
				self.logger.exception('Disconnect due to keep-alive ping error')
				self.__disconnect()
				continue
			self.__keep_alive_received.wait(self.KEEP_ALIVE_TIMEOUT)
			if not self.is_online():
				break
			if self.__keep_alive_received.is_set():
				self.__ping_array.append(time.monotonic() - time_sent)
				if len(self.__ping_array) > 5:
					self.__ping_array.pop(0)
				self.logger.debug('Keep-alive responded, ping = {}ms'.format(round(self.ping * 1000, 2)))
			else:
				self.logger.warning('Disconnect due to keep-alive ping timeout')
				self.__disconnect()
			for i in range(self.KEEP_ALIVE_INTERVAL * 10):
				time.sleep(0.1)
				if not self.is_online():
					break
