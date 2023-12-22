import traceback

from chatbridge.impl import utils
from chatbridge.impl.discord import stored, bot
from chatbridge.impl.discord.client import DiscordChatClient
from chatbridge.impl.discord.config import DiscordConfig

ConfigFile = 'ChatBridge_discord.json'


def main():
	stored.config = utils.load_config(ConfigFile, DiscordConfig)
	stored.client = DiscordChatClient.create(stored.config)
	stored.bot = bot.create_bot()
	utils.start_guardian(stored.client)
	utils.register_exit_on_termination()

	try:
		stored.bot.start_running()
	except (KeyboardInterrupt, SystemExit):
		stored.client.stop()
	except Exception:
		print(traceback.format_exc())

	print('Bye~')


if __name__ == '__main__':
	main()
