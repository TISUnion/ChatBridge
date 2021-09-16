from typing import Optional

from mcdreforged.api.all import *

from chatbridge.core.client import ChatBridgeClient
from chatbridge.core.config import ClientInfo
from chatbridge.core.network.basic import Address
from chatbridge.core.network.protocol import ChatContent
from chatbridge.impl.mcdr.config import MCDRClientConfig


class ChatBridgeMCDRClient(ChatBridgeClient):
	KEEP_ALIVE_THREAD_NAME = 'ChatBridge-KeepAlive'

	def __init__(self, config: MCDRClientConfig, server: ServerInterface):
		super().__init__(
			config.aes_key,
			Address(config.server_hostname, config.server_port),
			ClientInfo(name=config.name, password=config.password)
		)
		self.config = config
		self.server: Optional[ServerInterface] = server
		self.logger.removeHandler(self.logger.console_handler)
		self.logger.addHandler(self.server.logger.console_handler)

	def get_logging_name(self) -> str:
		return 'ChatBridge@{}'.format(hex((id(self) >> 16) & (id(self) & 0xFFFF))[2:].rjust(4, '0'))

	@classmethod
	def _get_main_loop_thread_name(cls):
		return 'ChatBridge-' + super()._get_main_loop_thread_name()

	@classmethod
	def _get_keep_alive_thread_name(cls):
		return 'ChatBridge-' + super()._get_keep_alive_thread_name()

	def _on_started(self):
		super()._on_started()
		self.logger.info('Connected to the server')

	def _on_stopped(self):
		super()._on_stopped()
		self.logger.info('Client stopped')
		try:
			from chatbridge.impl.mcdr import entry
			entry.client = None
		except ModuleNotFoundError:
			pass

	def _on_chat(self, sender: str, content: ChatContent):
		if self.server is not None:
			self.server.say(RText('[{}] {}'.format(sender, content.formatted_str()), RColor.gray))
