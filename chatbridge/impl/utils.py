import json
import os
import time
from threading import Thread
from typing import Type, TypeVar

from chatbridge.core.client import ChatBridgeClient
from chatbridge.core.config import BasicConfig

T = TypeVar('T', BasicConfig, BasicConfig)


def load_config(config_path: str, config_class: Type[T]) -> T:
	if not os.path.isfile(config_path):
		print('Configure file not found!'.format(config_path))
		with open(config_path, 'w') as file:
			json.dump(config_class.get_default().serialize(), file, ensure_ascii=False, indent=4)
		print('Default example configure generated'.format(config_path))
		raise FileNotFoundError(config_path)
	with open(config_path) as file:
		return config_class.deserialize(json.load(file))


def start_guardian(client: ChatBridgeClient) -> Thread:
	def loop():
		try:
			while True:
				if not client.is_online():
					client.start()
				time.sleep(3)
		except (KeyboardInterrupt, SystemExit):
			client.stop()

	thread = Thread(target=loop, args=())
	thread.setDaemon(True)
	thread.start()
	return thread
