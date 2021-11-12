from typing import List

from mcdreforged.utils.serializer import Serializable

from chatbridge.core.config import ClientConfig


class RconEntry(Serializable):
	name: str
	address: str
	port: int
	password: str


class OnlineConfig(ClientConfig):
	server_list: List[RconEntry] = [
		RconEntry(
			name='survival',
			address='127.0.0.1',
			port=25575,
			password='Server Rcon Password',
		)
	]
	bungeecord_list: List[RconEntry] = [
		RconEntry(
			name='BungeecordA',
			address='127.0.0.1',
			port=39999,
			password='Bungee Rcon Password',
		)
	]
	display_order: List[str] = [
		'survival',
		'creative'
	]
