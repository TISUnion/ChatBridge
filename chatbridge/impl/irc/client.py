from chatbridge.core.client import ChatBridgeClient
from chatbridge.core.network.protocol import ChatPayload, CommandPayload
from chatbridge.impl.irc import stored
from chatbridge.impl.irc.bot import MessageDataType


class IRCChatClient(ChatBridgeClient):
	def on_chat(self, sender: str, payload: ChatPayload):
		stored.bot.add_message((sender, payload), None, MessageDataType.CHAT)