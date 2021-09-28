import sys
from typing import Dict, Any, Callable

from chatbridge.common import constants
from chatbridge.impl.cli import cli_client, cli_server
from chatbridge.impl.cqhttp import entry as cqhttp
from chatbridge.impl.discord import entry as discord

ENTRY_MAPPING: Dict[str, Callable[[], Any]] = {
	'client': cli_client.main,
	'server': cli_server.main,
	'discordbot': discord.main,
	'cqhttpbot': cqhttp.main,
}


def main():
	if len(sys.argv) == 2:
		arg = sys.argv[1]
		entry = ENTRY_MAPPING.get(arg)
		if entry is not None:
			entry()
		else:
			print('Unknown argument {}'.format(arg))
	else:
		prefix = 'python -m {}'.format(constants.PACKAGE_NAME)
		print('{} client: Start a simple text-chatting-only ChatBridge client'.format(prefix))
		print('{} server: Start the ChatBridge server'.format(prefix))
		print('{} discordbot: Start a Discord bot as client'.format(prefix))
		print('{} cqhttpbot: Start a CQ-Http bot as client'.format(prefix))


if __name__ == '__main__':
	main()
