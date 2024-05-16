from mcdreforged.api.decorator import new_thread

from chatbridge.core.client import ChatBridgeClient
from chatbridge.core.network.protocol import ChatPayload, CommandPayload, CustomPayload
from chatbridge.impl.discord import stored
from chatbridge.impl.discord.bot import MessageDataType
from chatbridge.impl.tis.protocol import StatsQueryResult, OnlineQueryResult

from discord import Embed, Color, Client


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
			result: StatsQueryResult = StatsQueryResult.deserialize(payload.result)
			if result.success:
				bot.add_stats_result(result.stats_name, result.data, result.total, channel_id)
			else:
				if result.error_code == 1:
					message = 'Unknown or empty statistic'
				elif result.error_code == 2:
					message = 'StatsHelper plugin not found'
				else:
					message = 'Error code: {}'.format(result.error_code)
				bot.add_message(message, channel_id, MessageDataType.TEXT)
		elif payload.command == '!!online':
			result = OnlineQueryResult.deserialize(payload.result)
			bot.add_embed('{} online players'.format(stored.config.server_display_name), 'Player list', '\n'.join(result.data), channel_id)

	@new_thread('ChatBridge-discord-on-custom')
	def on_custom(self, sender: str, payload: CustomPayload):
		if payload.data['type'] == 'player-join-leave':
			player = payload.data['player']
			server = payload.data['server']
			color: Color
			msg: str

			if payload.data['join']:
				color = Color.green()
				msg = '加入了遊戲'
			else:
				color = Color.red()
				msg = '離開了遊戲'

			embed = Embed(description=f'**{server} ▶ {player} {msg}**', color=color)

			stored.bot.sync_webhook.send(embed=embed, username=stored.bot.user.name, avatar_url=stored.bot.user.avatar.url)
		elif payload.data['type'] == 'player-swap-server':
			player = payload.data['player']
			_from = payload.data['from']
			_to = payload.data['to']

			embed = Embed(description=f'**{_from} ▶ {player} 移動到 {_to}**', color=Color.blue())

			stored.bot.sync_webhook.send(embed=embed, username=stored.bot.user.name, avatar_url=stored.bot.user.avatar.url)
		elif payload.data['type'] == 'server-start-stop':
			server = sender
			color: Color
			emoji: str
			msg: str

			if payload.data['start']:
				color = Color.green()
				emoji = '🟢'
				msg = '已啟動'
			else:
				color = Color.red()
				emoji = '🔴'
				msg = '已關閉'

			embed = Embed(description=f'**{emoji} {server} 伺服器{msg}**', color=color)

			stored.bot.sync_webhook.send(embed=embed, username=stored.bot.user.name, avatar_url=stored.bot.user.avatar.url)
		elif payload.data['type'] == 'player-first-join':
			player = payload.data['player']

			embed = Embed(description=f'**有一隻新湯匙🥄 {player} 掉在新手村**', color=Color.gold())

			stored.bot.sync_webhook.send(embed=embed, username=stored.bot.user.name, avatar_url=stored.bot.user.avatar.url)
