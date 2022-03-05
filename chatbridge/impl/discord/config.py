from typing import List

from chatbridge.core.config import ClientConfig


class DiscordConfig(ClientConfig):
	bot_token: str = "your.bot.token.here"
	channels_for_command: List[int] = [
		123400000000000000,
		123450000000000000
	]
	channel_for_chat: int = 123400000000000000
	command_prefix: str = '!!'
	client_to_query_stats: str = 'MyClient1'
	client_to_query_online: str = 'MyClient2'
	embed_color: int = 3447003
	embed_icon_url: str = 'https://cdn.discordapp.com/emojis/566212479487836160.png'
	server_display_name: str = 'TIS'
