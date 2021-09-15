import json
import os
from typing import Type, TypeVar

from chatbridge.core.config import BasicConfig


T = TypeVar('T', BasicConfig, BasicConfig)


def load_config(config_path: str, config_class: Type[T]) -> T:
	if not os.path.isfile(config_path):
		print('Configure file not found!'.format(config_path))
		with open(config_path, 'w') as file:
			json.dump(config_class.get_default(), file, ensure_ascii=False, indent=4)
		print('Default example configure generated'.format(config_path))
		raise FileNotFoundError(config_path)
	with open(config_path) as file:
		return config_class.deserialize(json.load(file))
