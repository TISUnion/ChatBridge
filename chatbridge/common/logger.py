import os
import sys
import time
import weakref
import zipfile
from logging import FileHandler, Formatter, Logger, DEBUG, StreamHandler, INFO
from threading import RLock
from typing import Optional, Set

from colorlog import ColoredFormatter

LOGGING_DIR = os.path.join('logs')


class SyncStdoutStreamHandler(StreamHandler):
	__write_lock = RLock()

	def __init__(self):
		super().__init__(sys.stdout)

	def emit(self, record) -> None:
		with self.__write_lock:
			super().emit(record)


def _create_file_handler(name: str) -> FileHandler:
	logging_file_path: str = os.path.join(LOGGING_DIR, 'chatbridge_{}.log'.format(name))
	if not os.path.isdir(os.path.dirname(logging_file_path)):
		os.makedirs(os.path.dirname(logging_file_path))

	if os.path.isfile(logging_file_path):
		modify_time = '{}_{}'.format(time.strftime('%Y-%m-%d', time.localtime(os.stat(logging_file_path).st_mtime)), name)
		counter = 0
		while True:
			counter += 1
			zip_file_name = '{}/{}-{}.zip'.format(os.path.dirname(logging_file_path), modify_time, counter)
			if not os.path.isfile(zip_file_name):
				break
		zipf = zipfile.ZipFile(zip_file_name, 'w')
		zipf.write(logging_file_path, arcname=os.path.basename(logging_file_path), compress_type=zipfile.ZIP_DEFLATED)
		zipf.close()
		os.remove(logging_file_path)
	file_handler = FileHandler(logging_file_path, encoding='utf8')
	file_handler.setFormatter(Formatter(
		'[%(name)s] [%(asctime)s] [%(threadName)s/%(levelname)s]: %(message)s',
		datefmt='%Y-%m-%d %H:%M:%S'
	))
	return file_handler


class ChatBridgeLogger(Logger):
	LOG_COLORS = {
		'DEBUG': 'blue',
		'INFO': 'green',
		'WARNING': 'yellow',
		'ERROR': 'red',
		'CRITICAL': 'bold_red',
	}
	SECONDARY_LOG_COLORS = {
		'message': {
			'WARNING': 'yellow',
			'ERROR': 'red',
			'CRITICAL': 'red'
		}
	}
	__DEBUG_SWITCH = False
	__REFS: Set['ChatBridgeLogger'] = weakref.WeakSet()

	@classmethod
	def set_debug_all(cls, value: bool):
		cls.__DEBUG_SWITCH = value
		for logger in cls.__REFS:
			logger.__refresh_debug_level()

	def __init__(self, name: str, *, file_name: Optional[str] = None, file_handler: Optional[FileHandler] = None):
		super().__init__(name)
		self.console_handler = SyncStdoutStreamHandler()
		self.console_handler.setFormatter(ColoredFormatter(
			f'[%(name)s] [%(asctime)s] [%(threadName)s/%(log_color)s%(levelname)s%(reset)s]: %(message_log_color)s%(message)s%(reset)s',
			log_colors=self.LOG_COLORS,
			secondary_log_colors=self.SECONDARY_LOG_COLORS,
			datefmt='%H:%M:%S'
		))
		self.addHandler(self.console_handler)
		if file_name is not None and file_handler is None:
			self.file_handler = _create_file_handler(file_name)
		else:
			self.file_handler = file_handler
		if self.file_handler is not None:
			self.addHandler(self.file_handler)
		self.__REFS.add(self)
		self.__refresh_debug_level()

	@classmethod
	def is_debug_enabled(cls) -> bool:
		return cls.__DEBUG_SWITCH

	def __refresh_debug_level(self):
		self.setLevel(DEBUG if self.__DEBUG_SWITCH else INFO)

	def close_file(self):
		if self.file_handler is not None:
			self.removeHandler(self.file_handler)
			self.file_handler.close()
			self.file_handler = None
