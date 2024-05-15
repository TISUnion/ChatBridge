import uuid
from abc import ABC
from typing import List, Optional, Union

from mcdreforged.utils.serializer import Serializable
from mcdreforged.minecraft.rtext.text import *

from chatbridge.common.serializer import NoMissingFieldSerializable


# ==============
#     Packet
# ==============


class AbstractPacket(NoMissingFieldSerializable, ABC):
	pass


class LoginPacket(AbstractPacket):
	name: str
	password: str


class LoginResultPacket(AbstractPacket):
	message: str  # will be "ok"


class PacketType:
	keep_alive = 'chatbridge.keep_alive'
	chat = 'chatbridge.chat'
	discord_chat = 'chatbridge.discord_chat'
	command = 'chatbridge.command'
	custom = 'chatbridge.custom'


class ChatBridgePacket(AbstractPacket):
	sender: str
	receivers: List[str]
	broadcast: bool
	type: str
	payload: dict

# ==============
#     Payload
# ==============


class AbstractPayload(NoMissingFieldSerializable, ABC):
	pass


class KeepAlivePayload(AbstractPayload):
	_PING = 'ping'
	_PONG = 'pong'

	ping_type: str

	def is_ping(self) -> bool:
		return self.ping_type == self._PING

	def is_pong(self) -> bool:
		return self.ping_type == self._PONG

	@classmethod
	def ping(cls) -> 'KeepAlivePayload':
		return KeepAlivePayload(ping_type=cls._PING)

	@classmethod
	def pong(cls) -> 'KeepAlivePayload':
		return KeepAlivePayload(ping_type=cls._PONG)


class ChatPayload(AbstractPayload):
	author: str
	message: str

	def formatted_str(self) -> str:
		if self.author != '':
			return '<{}> {}'.format(self.author, self.message)
		else:
			return self.message

class DiscordChatPayload(AbstractPayload):
	role: str
	color: str
	author: str
	message: str
	reply_name: str
	reply_color: str
	reply_mes: str
	
	@property
	def rtext_list(self) -> RTextList:
		return RTextList(
			RTextList(
				'    §8┌──── §f<',
				RText(self.reply_name, color=RColorRGB.from_code(self.reply_color)),
				f'§f> §8{self.reply_mes}\n',
			) if self.reply_name else '',
			RText(f'[Discord] ', color=RColor.blue, styles=RStyle.bold),
			'< ',
			RText(self.role, color=RColorRGB.from_code(self.color)),
			f' | {self.author} > {self.message}'
		)

	def formatted_str(self) -> str:
		return self.rtext_list.to_json_str()

class CommandPayload(AbstractPayload):
	cid: str
	command: str
	responded: bool
	params: dict = {}
	result: dict

	@classmethod
	def ask(cls, command: str, params: Optional[Union[Serializable, dict]] = None) -> 'CommandPayload':
		if params is None:
			params = {}
		if isinstance(params, Serializable):
			params = params.serialize()
		return CommandPayload(
			cid=uuid.uuid4().hex,
			command=command,
			responded=False,
			params=params,
			result={},
		)

	@classmethod
	def answer(cls, asker_payload: 'CommandPayload', result: Union[Serializable, dict]) -> 'CommandPayload':
		if isinstance(result, Serializable):
			result = result.serialize()
		return CommandPayload(
			cid=asker_payload.cid,
			command=asker_payload.command,
			responded=True,
			params=asker_payload.params,
			result=result,
		)


class CustomPayload(AbstractPayload):
	data: dict
