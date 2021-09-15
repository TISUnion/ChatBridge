import socket
from threading import Thread, Event
from typing import Optional

from chatbridge.core.config import ClientInfo
from chatbridge.core.network.basic import Address
from chatbridge.core.network.connection import ChatBridgeConnection
from chatbridge.core.network.protocol import LoginPacket


class ChatBridgeClient(ChatBridgeConnection):
	def __init__(self, aes_key: str, address: Address, info: ClientInfo, *, name: Optional[str] = None):
		if name is None:
			name = info.name
		super().__init__(name, aes_key, address)
		self.__info = info
		self.__thread_keep_alive: Optional[Thread] = None
		self.__login_done = Event()

	def stop(self):
		self.logger.info('Stopping client')
		self._stopping_flag = True
		self.disconnect()
		super().stop()

	def is_online(self) -> bool:
		return self._is_connected() and self._is_running()

	def start(self):
		"""
		Start the client and related threads, and wait until the login part ends
		"""
		super().start()
		self.__login_done.wait()

	def _login(self):
		self.connect()
		self.send_packet(LoginPacket(name=self.__info.name, password=self.__info.password))

	def _main_loop(self):
		try:
			self._login()
		except:
			self.logger.exception('Failed to connect to the server and login')
		finally:
			self.__login_done.set()
		if not self._is_connected():
			return
		self._on_started()
		try:
			while self._is_connected() and not self._is_stopping():
				try:
					self._tick_connection()
				except socket.error:
					if not self._is_stopping():
						self.logger.exception('Failed to receive data, stopping client now')
					break
				except:
					if not self._is_stopping():
						if self._is_connected():  # might already been handled and disconnected
							self.logger.exception('Error ticking client connection')
					break
		finally:
			self.disconnect()

	def _on_started(self):
		self._start_keep_alive_thread()
