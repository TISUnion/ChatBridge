import json
import socket
import time
from socket import timeout
from threading import Lock, Event, RLock
from typing import Optional, Iterable, Dict, Callable, Any

from chatbridge.common import constants
from chatbridge.core.network import net_util
from chatbridge.core.network.basic import ChatBridgeBase, Address
from chatbridge.core.network.protocol import ChatBridgePacket, PacketType, AbstractPacket, ChatContent


class ChatBridgeConnection(ChatBridgeBase):
	KEEP_ALIVE_INTERVAL = 60
	KEEP_ALIVE_TIMEOUT = 15
	_PACKET_CALLBACK = Callable[[dict], Any]
	TIMEOUT = 5

	def __init__(self, name: str, aes_key: str, address: Address):
		super().__init__(name, aes_key)
		self._address: Address = address
		self._sock: Optional[socket.socket] = None
		self.__sock_lock = RLock()
		self.__communication_dict: Dict[str, Callable[[dict], Any]] = {}  # c_id -> callback
		self.__communication_dict_lock = Lock()
		self.__keep_alive_received = Event()
		self.__ping_array = []

	# --------------
	#   Connection
	# --------------

	@property
	def ping(self) -> float:
		"""
		ping in second
		"""
		return -1 if len(self.__ping_array) == 0 else sum(self.__ping_array) / len(self.__ping_array)

	def connect(self):
		with self.__sock_lock:
			if self._is_connected():
				raise RuntimeError('Already connected')
			self._sock = socket.socket()
			self.logger.info('Connecting to {}'.format(self._address.pretty_str()))
			try:
				self._sock.connect(self._address)
			except Exception as e:
				self._sock = None
				raise e from None

	def disconnect(self):
		with self.__sock_lock:
			if self._is_connected():
				sock = self._sock
				self._sock = None
				try:
					sock.close()
				except:
					pass

	def _is_connected(self) -> bool:
		return self._sock is not None

	def _tick_connection(self):
		try:
			# self.logger.debug('Waiting for data received')
			data_string = net_util.receive_data(self._sock, self._cryptor, timeout=self.TIMEOUT)
		except timeout:
			# self.logger.debug('Timeout, ignore')
			pass
		except (ConnectionResetError, net_util.EmptyContent) as e:
			self.logger.warning('Connection closed: {}'.format(e))
			self.disconnect()
		else:
			# self.logger.debug('Received {}'.format(data_string))
			self.process_data(data_string)

	def process_data(self, data_string: str):
		try:
			js_dict = json.loads(data_string)
		except ValueError:
			self.logger.exception('Fail to decode received string: {}'.format(data_string))
			return
		try:
			packet = ChatBridgePacket.deserialize(js_dict)
		except:
			self.logger.exception('Fail to deserialize received json: {}'.format(js_dict))
			return
		try:
			self._on_packet(packet)
		except:
			self.logger.exception('Fail to process packet {}'.format(packet))

	# ----------------
	#   Packet Logic
	# ----------------

	def send_packet(self, packet: AbstractPacket):
		if self._is_connected():
			net_util.send_data(self._sock, self._cryptor, packet)
		else:
			self.logger.warning('Trying to send a packet when not connected')

	def __communicate(self, type_: str, receiver: Iterable[str], content: dict, *, is_broadcast: bool):
		self.send_packet(ChatBridgePacket(
			sender=self.get_name(),
			receivers=list(receiver),
			broadcast=is_broadcast,
			type=type_,
			content=content
		))

	def communicate_to_clients(self, type_: str, clients: Iterable[str], content: dict):
		return self.__communicate(type_, clients, content, is_broadcast=False)

	def communicate_to_client(self, type_: str, name: str, content: dict):
		return self.communicate_to_clients(type_, [name], content)

	def communicate_to_server(self, type_: str, content: dict,):
		self.communicate_to_client(type_, constants.SERVER_NAME, content)

	def communicate_to_all(self, type_: str, content: dict):
		self.__communicate(type_, [], content, is_broadcast=True)

	def _on_packet(self, packet: ChatBridgePacket):
		if packet.type == PacketType.keep_alive:
			if packet.content['ping_type'] == 'ping':
				self.communicate_to_client(PacketType.keep_alive, packet.sender, {'ping_type': 'pong'})
			else:
				self.__keep_alive_received.set()
		if packet.type == PacketType.chat:
			self._on_chat(packet.sender, ChatContent.deserialize(packet.content))

	def _on_chat(self, sender: str, content: ChatContent):
		pass

	def send_chat(self, message: str):
		self.communicate_to_all(PacketType.chat, ChatContent(message=message).serialize())

	# --------------
	#   Keep Alive
	# --------------

	def _start_keep_alive_thread(self):
		self._start_thread(self._keep_alive_loop, 'KeepAlive')

	def _keep_alive_loop(self):
		"""
		Except to have the same life-span as the connection
		"""
		while self._is_connected():
			self.__keep_alive_received.clear()
			time_sent = time.time()
			self.communicate_to_server(PacketType.keep_alive, {'ping_type': 'ping'})
			self.__keep_alive_received.wait(self.KEEP_ALIVE_TIMEOUT)
			if self.__keep_alive_received.is_set():
				self.__ping_array.append(time.time() - time_sent)
				if len(self.__ping_array) > 5:
					self.__ping_array.pop(0)
				self.logger.debug('Keep-alive responded, ping = {}ms'.format(round(self.ping * 1000, 2)))
			else:
				self.logger.warning('Disconnect due to keep-alive ping timeout')
				self.disconnect()
			time.sleep(self.KEEP_ALIVE_INTERVAL)
