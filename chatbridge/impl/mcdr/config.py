from typing import Optional

from chatbridge.core.config import ClientConfig
from chatbridge.common.serializer import NoMissingFieldSerializable

class SendToChatBridge(NoMissingFieldSerializable):
	chat: bool
	player_joined: bool
	player_left: bool
	server_start: bool
	server_stop: bool


class SendToMinecraft(NoMissingFieldSerializable):
	chat: bool
	discord_chat: bool
	server_info: bool
	player_join_leave: bool
	player_swap_server: bool
	server_start_stop: bool

class MCDRClientConfig(ClientConfig):
	enable: bool = True
	debug: bool = False
	client_to_query_online: Optional[str] = None
	send_to_chat_bridge: SendToChatBridge = SendToChatBridge(
		chat = True,
		player_joined = True,
		player_left = True,
		server_start = True,
		server_stop = True
	)
	send_to_minecraft: SendToMinecraft = SendToMinecraft(
		chat = True,
		discord_chat = True,
		server_info = True,
		player_join_leave = True,
		player_swap_server = True,
		server_start_stop = True
	)

