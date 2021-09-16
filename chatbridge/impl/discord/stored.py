from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from chatbridge.impl.discord.bot import DiscordBot
	from chatbridge.impl.discord.client import DiscordChatClient
	from chatbridge.impl.discord.config import DiscordConfig


config: 'DiscordConfig'
bot: 'DiscordBot'
client: 'DiscordChatClient'
