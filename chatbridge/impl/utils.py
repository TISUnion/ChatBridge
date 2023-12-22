import json
import os
import queue
import signal
import sys
import time
from threading import Thread
from typing import Type, TypeVar, Callable

from chatbridge.core.client import ChatBridgeClient
from chatbridge.core.config import BasicConfig

T = TypeVar('T', BasicConfig, BasicConfig)


def load_config(config_path: str, config_class: Type[T]) -> T:
	config = config_class.get_default()
	if not os.path.isfile(config_path):
		print('Configure file not found!'.format(config_path))
		with open(config_path, 'w', encoding='utf8') as file:
			json.dump(config.serialize(), file, ensure_ascii=False, indent=4)
		print('Default example configure generated'.format(config_path))
		raise FileNotFoundError(config_path)
	else:
		with open(config_path, encoding='utf8') as file:
			vars(config).update(vars(config_class.deserialize(json.load(file))))
		with open(config_path, 'w', encoding='utf8') as file:
			json.dump(config.serialize(), file, ensure_ascii=False, indent=4)
		return config


def start_guardian(client: ChatBridgeClient, wait_time: float = 10, loop_condition: Callable[[], bool] = lambda: True) -> Thread:
	def loop():
		first = True
		while loop_condition():
			if not client.is_running():
				client.logger.info('Guardian triggered {}'.format('start' if first else 'restart'))
				client.start()
			first = False
			time.sleep(wait_time)
		client.logger.info('Guardian stopped')

	thread = Thread(name='ChatBridge Guardian', target=loop, daemon=True)
	thread.start()
	return thread


def wait_until_terminate():
	q = queue.Queue()
	signal.signal(signal.SIGINT, lambda s, _: q.put(s))
	signal.signal(signal.SIGTERM, lambda s, _: q.put(s))
	sig = q.get()
	print('Interrupted with {} ({})'.format(signal.Signals(sig).name, sig))


def register_exit_on_termination():
	def callback(sig, _):
		print('Interrupted with {} ({}), exiting'.format(signal.Signals(sig).name, sig))
		sys.exit(0)

	signal.signal(signal.SIGINT, callback)
	signal.signal(signal.SIGTERM, callback)
