import json
import socket
import time
from concurrent.futures.thread import ThreadPoolExecutor
from threading import Thread, Event, RLock, Lock, current_thread
from typing import Dict, Optional, List, NamedTuple

from chatbridge.common import constants
from chatbridge.core.client import ChatBridgeClient, ClientStatus
from chatbridge.core.config import ClientInfo
from chatbridge.core.network import net_util
from chatbridge.core.network.basic import Address, ChatBridgeBase
from chatbridge.core.network.protocol import LoginPacket, ChatBridgePacket, AbstractPacket, LoginResultPacket, \
	PacketType, ChatPayload


class _ClientConnection(ChatBridgeClient):
	def __init__(self, server: 'ChatBridgeServer', info: ClientInfo):
		self.info = info
		self.server = server
		super().__init__(server.aes_key, ClientInfo(name=constants.SERVER_NAME, password=''))
		self.logger.addHandler(self.server.logger.file_handler)

	def get_logging_name(self) -> str:
		return 'Server.{}'.format(self.get_connection_client_name())

	def _get_main_loop_thread_name(self):
		return super()._get_main_loop_thread_name() + '.' + self.get_connection_client_name()

	def _get_keep_alive_thread_name(self):
		return super()._get_main_loop_thread_name() + '.' + self.get_connection_client_name()

	def get_logging_file_name(self) -> Optional[str]:
		return None

	def get_connection_client_name(self) -> str:
		return self.info.name

	def _keep_alive_target(self) -> str:
		return self.get_connection_client_name()

	def _connect_and_login(self):
		"""
		No need to login for this class
		"""
		self._set_status(ClientStatus.CONNECTED)
		self._send_packet(LoginResultPacket(message='ok'))

	def _send_packet(self, packet: AbstractPacket):
		super()._send_packet(packet)
		self.server.log_packet(packet, to_client=True, client_name=self.get_connection_client_name())

	def send_packet_invoker(self, packet: AbstractPacket):
		self._send_packet(packet)

	def _on_packet(self, packet: ChatBridgePacket):
		super()._on_packet(packet)
		self.server.process_packet(self, packet)

	def _on_started(self):
		super()._on_started()
		self.logger.info('Started client connection')

	def _on_stopped(self):
		super()._on_stopped()
		self.logger.info('Stopped client connection')

	def restart_connection(self, conn: socket.socket, addr: Address):
		if not self._is_stopped():
			self.stop()
		self.set_server_address(addr)
		self._set_socket(conn)
		self.start()


class ComingConnection(NamedTuple):
	sock: socket.socket
	addr: Address
	thread: Thread
	start_time: float

	@classmethod
	def create(cls, sock: socket.socket, addr: Address) -> 'ComingConnection':
		return ComingConnection(sock=sock, addr=addr, thread=current_thread(), start_time=time.time())


class ChatBridgeServer(ChatBridgeBase):
	MAXIMUM_LOGIN_DURATION = 20  # 20s

	def __init__(self, aes_key: str, server_address: Address):
		super().__init__('Server', aes_key)
		self.server_address = server_address
		self.clients: Dict[str, _ClientConnection] = {}
		self.__coming_connections: List[ComingConnection] = []
		self.__coming_connections_lock = Lock()
		self.__sock: Optional[socket.socket] = None
		self.__thread_run: Optional[Thread] = None
		self.__stop_lock = RLock()
		self.__stopping_flag = False
		self.__binding_done = Event()

	@classmethod
	def _get_main_loop_thread_name(cls):
		return 'ServerThread'

	def add_client(self, client_info: ClientInfo):
		self.clients[client_info.name] = _ClientConnection(self, client_info)

	def is_running(self) -> bool:
		return not self.__stopping_flag

	def _main_loop(self):
		self.__sock = socket.socket()
		self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			self.__sock.bind(self.server_address)
		except:
			self.logger.exception('Failed to bind {}'.format(self.server_address))
			self.__stopping_flag = True
			return
		finally:
			self.__binding_done.set()
		try:
			self.__sock.listen(5)
			self.__sock.settimeout(3)
			self.logger.info('Server started at {}'.format(self.server_address))
			counter = 0
			while self.is_running():
				try:
					self.__trim_coming_connections()
					try:
						conn, addr = self.__sock.accept()
					except socket.timeout:
						continue
					if not self.is_running():
						conn.close()
						break
					address = Address(*addr)
					counter += 1
					self.logger.info('New connection #{} from {}'.format(counter, address))
					Thread(name='Connection#{}'.format(counter), target=self.__handle_connection, args=(conn, address), daemon=True).start()
				except:
					if not self.__stopping_flag:
						self.logger.exception('Error ticking server')
		finally:
			self.__stop()
		self.logger.info('bye')

	def start(self):
		"""
		Start and wait until port binding done
		"""
		self.__binding_done.clear()
		super().start()
		self.__binding_done.wait()

	def __stop(self):
		self.__stopping_flag = True
		with self.__stop_lock:
			if self.__sock is not None:
				try:
					self.__sock.close()
					with ThreadPoolExecutor(max_workers=len(self.clients)) as worker:
						for client in self.clients.values():
							if client.is_running():
								worker.submit(client.stop)
					self.__sock = None
					self.logger.info('Socket closed')
				except:
					self.logger.exception('Error when stop close')

	def stop(self):
		self.__stop()
		super().stop()

	def __trim_coming_connections(self):
		with self.__coming_connections_lock:
			to_be_removed = []
			current_time = time.time()
			for cc in self.__coming_connections:
				if current_time - cc.start_time > self.MAXIMUM_LOGIN_DURATION:
					self.logger.warning('Terminating coming connection from {} in thread {} due to login timeout'.format(cc.addr, cc.thread.getName()))
					try:
						cc.sock.close()
					except:
						self.logger.exception('Error terminating coming connection from {} in thread {}'.format(cc.addr, cc.thread.getName()))
					to_be_removed.append(cc)
			for cc in to_be_removed:
				self.__coming_connections.remove(cc)

	def __handle_connection(self, conn: socket, addr: Address):
		success = False
		cc = ComingConnection.create(conn, addr)
		with self.__coming_connections_lock:
			self.__coming_connections.append(cc)
		try:
			try:
				recv_str = net_util.receive_data(conn, self._cryptor, timeout=15)
				login_packet = LoginPacket.deserialize(json.loads(recv_str))
			except Exception as e:
				self.logger.error('Failed reading client\'s login packet: {}'.format(e))
				return
			else:
				self.log_packet(login_packet, to_client=False)
				client = self.clients.get(login_packet.name, None)
				if client is not None:
					if client.info.password == login_packet.password:
						success = True
						self.logger.info('Identification of {} confirmed: {}'.format(addr, client.info.name))
						client.restart_connection(conn, addr)
					else:
						self.logger.warning('Wrong password during login for client {}: expected {} but received {}'.format(client.info.name, client.info.password, login_packet.password))
				else:
					self.logger.warning('Unknown client name during login: {}'.format(login_packet.name))
			if not success:
				conn.close()
				self.logger.warning('Closed connection from {}'.format(addr))
		finally:
			with self.__coming_connections_lock:
				try:
					self.__coming_connections.remove(cc)
				except ValueError:
					pass

	def log_packet(self, packet: AbstractPacket, *, to_client: bool, client_name: str = None):
		if isinstance(packet, ChatBridgePacket):
			if to_client:
				assert client_name is not None
				indicator = '-> {}'.format(client_name)
			else:
				indicator = '{} -> {}'.format(packet.sender, ','.join(packet.receivers) if not packet.broadcast else '*')
			self.logger.debug('[{}] {}: {}'.format(indicator, packet.type, packet.payload))
		else:
			if to_client:
				indicator = '{} -> ?'.format(constants.SERVER_NAME)
			else:
				indicator = '? -> {}'.format(constants.SERVER_NAME)
			self.logger.debug('[{}] {}: {}'.format(indicator, packet.__class__.__name__, packet.serialize()))

	def process_packet(self, client: _ClientConnection, packet: ChatBridgePacket):
		if packet.sender != client.info.name:
			self.logger.warning('Un-matched sender name during packet transferring, expected {} but found {}'.format(client.info.name, packet.sender))
			return
		self.log_packet(packet, to_client=False)
		if packet.type == PacketType.chat:
			try:
				self.on_chat(client.get_connection_client_name(), ChatPayload.deserialize(packet.payload))
			except:
				self.logger.exception('Error when deserialize chat packet from {}'.format(
					client.get_connection_client_name()))
		receivers = packet.receivers if not packet.broadcast else self.clients.keys()
		for receiver_name in set(receivers):
			if receiver_name != packet.sender:
				if receiver_name == constants.SERVER_NAME:
					self.on_packet(packet)
				else:
					client = self.clients.get(receiver_name)
					if client is not None:
						if client.is_online():
							client.send_packet_invoker(packet)
					else:
						self.logger.warning('Unknown client name {}'.format(receiver_name))

	def on_chat(self, sender: str, content: ChatPayload):
		pass

	def on_packet(self, packet: ChatBridgePacket):
		pass
