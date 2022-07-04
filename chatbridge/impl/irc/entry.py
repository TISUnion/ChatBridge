import traceback

from chatbridge.impl import utils
from chatbridge.impl.irc import stored, bot
from chatbridge.impl.irc.client import IRCChatClient
from chatbridge.impl.irc.config import IRCConfig

ConfigFile = 'ChatBridge_irc.json'


def main():
	stored.config = utils.load_config(ConfigFile, IRCConfig)
	stored.client = IRCChatClient.create(stored.config)
	stored.bot = bot.create_bot()
	utils.start_guardian(stored.client)

	try:
		stored.bot.start_running()
	except (KeyboardInterrupt, SystemExit):
		stored.client.stop()
	except:
		print(traceback.format_exc())
	print('Bye~')


if __name__ == '__main__':
	main()
