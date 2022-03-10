from threading import Thread, current_thread, RLock
from typing import NamedTuple, Callable, Optional

from chatbridge.common.logger import ChatBridgeLogger
from chatbridge.core.network.cryptor import AESCryptor


class Address(NamedTuple):
	hostname: str
	port: int

	def __str__(self):
		return '{}:{}'.format(self.hostname, self.port)


class ChatBridgeBase:
	def __init__(self, name: str, aes_key: str):
		super().__init__()
		self.__name = name
		self.logger = ChatBridgeLogger(self.get_logging_name(), file_name=self.get_logging_file_name())
		self.aes_key = aes_key
		self._cryptor = AESCryptor(aes_key)
		self.__thread_run: Optional[Thread] = None
		self.__thread_run_lock = RLock()

	def get_name(self) -> str:
		return self.__name

	def get_logging_name(self) -> str:
		return self.get_name()

	def get_logging_file_name(self) -> Optional[str]:
		"""
		None for no file handler
		"""
		return type(self).__name__

	def _start_thread(self, target: Callable, name: str) -> Thread:
		thread = Thread(target=target, args=(), name=name, daemon=True)
		thread.start()
		self.logger.debug('Started thread {}: {}'.format(name, thread))
		return thread

	def _get_main_loop_thread_name(cls):
		return 'MainLoop'

	def start(self):
		def func():
			self._main_loop()
			self.logger.close_file()
			with self.__thread_run_lock:
				self.__thread_run = None

		with self.__thread_run_lock:
			if self.__thread_run is not None:
				raise RuntimeError('Already running')
			self.__thread_run = self._start_thread(func, self._get_main_loop_thread_name())

	def stop(self):
		"""
		Stop the client/server, and wait until the MainLoop thread exits
		Need to be called on a non-MainLoop thread
		"""
		self.logger.debug('Joining MainLoop thread')
		with self.__thread_run_lock:
			thread = self.__thread_run
		if thread is not None:
			if thread is not current_thread():
				thread.join()
			else:
				self.logger.warning('Joining current thread {}'.format(thread))
		self.logger.debug('Joined MainLoop thread')

	def _main_loop(self):
		pass
