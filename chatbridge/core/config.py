from abc import ABC
from typing import List

from chatbridge.common.serializer import Serializable


class BasicConfig(Serializable, ABC):
	aes_key: str = 'ThisIstheSecret'


class ClientConfig(BasicConfig):
	name: str = 'MyClientName'
	password: str = 'MyClientPassword'
	server_hostname: str = '127.0.0.1'
	server_port: int = 30001


class ClientInfo(Serializable):
	name: str
	password: str


class ServerConfig(BasicConfig):
	hostname: str = 'localhost'
	port: int = 30001
	clients: List[ClientInfo] = []
