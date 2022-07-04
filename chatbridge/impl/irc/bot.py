import asyncio
from email import message
from enum import auto, Enum
from queue import Queue, Empty
from typing import NamedTuple, Any, List

import irc.client
import irc.client_aio

from chatbridge.common import logger
from chatbridge.core.network.protocol import ChatPayload
from chatbridge.impl.irc import stored
from chatbridge.impl.irc.config import IRCConfig


class MessageDataType(Enum):
	CHAT = auto()

class MessageData(NamedTuple):
	channel: str
	data: Any
	type: MessageDataType

class IRCBot(irc.client_aio.AioSimpleIRCClient):
	@property
	def config(self) -> IRCConfig:
		return stored.config
	
	def __init__(self):
		irc.client.SimpleIRCClient.__init__(self)
		self.messages = Queue()
		self.logger = logger.ChatBridgeLogger('Bot', file_handler=stored.client.logger.file_handler)

	def start_running(self):
		self.logger.info('Starting the bot')
		try:
			self.connect(self.config.ircserver, self.config.ircport, self.config.nickname, password=self.config.ircpassword)
			self.start()
		except irc.client.ServerConnectionError as x:
			print(x)

	def on_welcome(self, connection, event):
		self.logger.info(f'Logged in as {self.config.nickname}')
		if irc.client.is_channel(self.config.channel):
			connection.join(self.config.channel)
		else:
			self.future = asyncio.ensure_future(
				self.send_queue(), loop=connection.reactor.loop
			)

	def on_join(self, connection, event):
		self.future = asyncio.ensure_future(
			self.send_queue(), loop=connection.reactor.loop
		)

	def on_disconnect(self, connection, event):
		self.future.cancel()
	
	def add_message(self, data, channel_id, t):
		self.messages.put(MessageData(data=data, channel=channel_id, type=t))

	def on_pubmsg(self, c, e):
		if e.source.nick == self.config.nickname:
			return
		if e.target == self.config.channel:
			msg_debug = f'{e.target}: {e.source.nick}: {e.arguments[0]}'
			args = e.arguments[0].split(' ')
			# Chat
			if e.target == self.config.channel:
				self.logger.info('Chat: {}'.format(msg_debug))
				stored.client.send_chat(e.arguments[0], author=e.source.nick)
	
	def on_privmsg(self, c, e):
		if e.source.nick == self.config.nickname:
			return
		if e.target == self.config.channel:
			msg_debug = f'{e.target}: {e.source.nick}: {e.arguments[0]}'
			args = e.arguments[0].split(' ')
			# Chat
			if e.target == self.config.channel:
				self.logger.info('Chat: {}'.format(msg_debug))
				stored.client.send_chat(e.arguments[0], author=e.source.nick)

	async def send_queue(self):
		while 1:
			try:
				message_data = self.messages.get(block=False)  # type: MessageData
			except Empty:
				await asyncio.sleep(0.05)
				continue
			data = message_data.data
			if message_data.type == MessageDataType.CHAT:  # chat message
				assert isinstance(data, tuple)
				sender: str = data[0]
				payload: ChatPayload = data[1]
				self.connection.privmsg(self.config.channel, '[{}] {}'.format(sender, payload.formatted_str()))
			else:
				self.logger.debug('Unknown messageData type {}'.format(message_data.data))

def create_bot() -> IRCBot:
	config = stored.config
	bot = IRCBot()
	return bot