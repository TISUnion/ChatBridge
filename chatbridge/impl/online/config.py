from typing import List

from mcdreforged.utils.serializer import Serializable

from chatbridge.core.config import ClientConfig


class _Entry(Serializable):
	name: str
	address: str
	port: int
	password: str


class OnlineConfig(ClientConfig):
	bungeecord_list: List[_Entry] = [
		_Entry(
			name='BungeecordA',
			address='127.0.0.1',
			port='3999',
			password='Bungee Rcon Password',
		)
	]
