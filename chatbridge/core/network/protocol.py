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
	author: str
	message: str

	def formatted_str(self) -> str:
		if self.author != '':
			return '<{}> {}'.format(self.author, self.message)
		else:
			return self.message
