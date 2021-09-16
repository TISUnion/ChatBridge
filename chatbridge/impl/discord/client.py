from chatbridge.core.client import ChatBridgeClient
from chatbridge.core.config import ClientInfo
from chatbridge.core.network.basic import Address
from chatbridge.core.network.protocol import ChatContent, ChatBridgePacket
from chatbridge.impl.discord import stored
from chatbridge.impl.discord.bot import MessageDataType
from chatbridge.impl.discord.config import DiscordConfig


class DiscordChatClient(ChatBridgeClient):
	def __init__(self, config: DiscordConfig):
		server_address = Address(config.server_hostname, config.server_port)
		super().__init__(config.aes_key, server_address, ClientInfo(name=config.name, password=config.password))

	def _on_chat(self, sender: str, content: ChatContent):
		stored.bot.add_message(content, None, MessageDataType.CHAT)

	def _on_packet(self, packet: ChatBridgePacket):
		try:
			channel_id = packet.content['from_channel']
		except:
			self.logger.warning('No channel id in command response data: {}'.format(data))
			return
		bot = stored.bot
		if packet.type == 'stats_query':
			result_type = result['type']
			if result_type == 0:
				bot.addResult(result['stats_name'], result['result'], 'Stats Rank', channel_id)
			elif result_type == 1:
				bot.add_message('Stats not found', channel_id, MessageDataType.TEXT)
			elif result_type == 2:
				bot.add_message('StatsHelper plugin not loaded', channel_id, MessageDataType.TEXT)
		elif data['command'] == '!!online':
			result_type = result['type']
			if result_type == 0:
				bot.addResult('Player list', result['result'], 'TIS Online players', channel_id)
			elif result_type == 1:
				bot.add_message('Online list query failed', channel_id, MessageDataType.TEXT)
			elif result_type == 2:
				bot.add_message('Rcon is not working', channel_id, MessageDataType.TEXT)
