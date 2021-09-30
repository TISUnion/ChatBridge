from abc import ABC
from typing import List

from mcdreforged.utils.serializer import Serializable

from chatbridge.common.serializer import NoMissingFieldSerializable
from chatbridge.core.network.basic import Address


class BasicConfig(Serializable, ABC):
	aes_key: str = 'ThisIstheSecret'


class ClientInfo(NoMissingFieldSerializable):
	name: str
	password: str


class ClientConfig(BasicConfig):
	name: str = 'MyClientName'
	password: str = 'MyClientPassword'
	server_hostname: str = '127.0.0.1'
	server_port: int = 30001

	@property
	def client_info(self) -> ClientInfo:
		return ClientInfo(name=self.name, password=self.password)

	@property
	def server_address(self) -> Address:
		return Address(hostname=self.server_hostname, port=self.server_port)


class ServerConfig(BasicConfig):
	hostname: str = 'localhost'
	port: int = 30001
	clients: List[ClientInfo] = [
		ClientInfo(name='MyClientName', password='MyClientPassword')
	]
