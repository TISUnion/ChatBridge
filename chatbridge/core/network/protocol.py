from abc import ABC
from typing import List

from chatbridge.common.serializer import Serializable


class AbstractPacket(Serializable, ABC):
	pass


class LoginPacket(AbstractPacket):
	name: str
	password: str


class PacketType:
	keep_alive = 'chatbridge.keep_alive'
	chat = 'chatbridge.chat'


class ChatBridgePacket(AbstractPacket):
	sender: str
	receivers: List[str]
	broadcast: bool
	type: str
	content: dict


class ChatContent(Serializable):
	message: str

