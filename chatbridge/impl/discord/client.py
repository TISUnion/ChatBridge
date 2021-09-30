from chatbridge.core.client import ChatBridgeClient
from chatbridge.core.network.protocol import ChatPayload, CommandPayload
from chatbridge.impl.discord import stored
from chatbridge.impl.discord.bot import MessageDataType
from chatbridge.impl.tis.protocol import StatsQueryResult, OnlineQueryResult


class DiscordChatClient(ChatBridgeClient):
	def on_chat(self, sender: str, payload: ChatPayload):
		stored.bot.add_message((sender, payload), None, MessageDataType.CHAT)

	def on_command(self, sender: str, payload: CommandPayload):
		try:
			channel_id = payload.params['from_channel']
		except KeyError:
			self.logger.warning('No channel id in command response data: {}'.format(payload.params))
			return
		bot = stored.bot
		if payload.command.startswith('!!stats '):
			result = StatsQueryResult.deserialize(payload.result)
			if result.success:
				bot.add_stats_result(result.stats_name, result.data, result.total, channel_id)
			else:
				bot.add_message(result.message, channel_id, MessageDataType.TEXT)
		elif payload.command == '!!online':
			result = OnlineQueryResult.deserialize(payload.result)
			bot.add_embed('TIS Online players', 'Player list', '\n'.join(result.data), channel_id)
