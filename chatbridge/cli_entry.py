import sys

from chatbridge.common import constants

__all__ = [
	'main'
]


def client():
	from chatbridge.impl.cli import cli_client
	cli_client.main()


def server():
	from chatbridge.impl.cli import cli_server
	cli_server.main()


def discord_bot():
	from chatbridge.impl.discord import entry
	entry.main()


def cqhttp_bot():
	from chatbridge.impl.cqhttp import entry
	entry.main()


def online_command():
	from chatbridge.impl.online import entry
	entry.main()


def main():
	if len(sys.argv) == 2:
		arg = sys.argv[1]
		entry = globals().get(arg)
		if entry is not None and entry not in __all__ and callable(entry):
			entry()
		else:
			print('Unknown argument {}'.format(arg))
	else:
		prefix = 'python -m {}'.format(constants.PACKAGE_NAME)
		print('{} client: Start a simple text-chatting-only ChatBridge client'.format(prefix))
		print('{} server: Start the ChatBridge server'.format(prefix))
		print('{} discord_bot: Start a Discord bot as client'.format(prefix))
		print('{} cqhttp_bot: Start a CQ-Http bot as client'.format(prefix))
		print('{} online_command: Start a CQ-Http bot as client'.format(prefix))

