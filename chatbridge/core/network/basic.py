from threading import Thread, Event, current_thread
from typing import Optional, NamedTuple, Callable

from chatbridge.common.logger import ChatBridgeLogger
from chatbridge.core.network.cryptor import AESCryptor


class Address(NamedTuple):
	hostname: str
	port: int

	def pretty_str(self) -> str:
		return '{}:{}'.format(self.hostname, self.port)


class ChatBridgeBase:
	def __init__(self, name: str, aes_key: str):
		super().__init__()
		self.__name = name
		self.logger = ChatBridgeLogger(self.get_logging_name())
		self.aes_key = aes_key
		self._cryptor = AESCryptor(aes_key)
		self.__thread_run: Optional[Thread] = None
		self._stopping_flag = False

	def get_name(self) -> str:
		return self.__name

	def get_logging_name(self) -> str:
		return self.get_name()

	@staticmethod
	def _start_thread(target: Callable, name: str) -> Thread:
		thread = Thread(target=target, args=(), name=name, daemon=True)
		thread.start()
		return thread

	@classmethod
	def _get_main_loop_thread_name(cls):
		return 'MainLoop'

	def start(self):
		if self._is_running():
			raise RuntimeError('Already running')

		def func():
			self._on_starting()
			self._main_loop()
			self._on_stopped()

		self.__thread_run = self._start_thread(func, self._get_main_loop_thread_name())

	def _main_loop(self):
		pass

	def stop(self):
		"""
		Stop the client/server, and wait until the MainLoop thread exits
		Need to be called on a non-MainLoop thread
		"""
		if self._is_running():
			self._stopping_flag = True
			thread = self.__thread_run
			if thread is not None and thread is not current_thread():
				thread.join()

	def _is_running(self) -> bool:
		return self.__thread_run is not None

	def _is_stopping(self) -> bool:
		return self._stopping_flag

	def _on_starting(self):
		pass

	def _on_stopped(self):
		self.logger.removeHandler(self.logger.file_handler)
		self.logger.file_handler.close()
		self.__thread_run = None
