from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from chatbridge.impl.irc.bot import IRCBot
	from chatbridge.impl.irc.client import IRCChatClient
	from chatbridge.impl.irc.config import IRCConfig


config: 'IRCConfig'
bot: 'IRCBot'
client: 'IRCChatClient'
