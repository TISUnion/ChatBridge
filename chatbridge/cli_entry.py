import sys
from typing import Dict, Any, Callable

from chatbridge.common import constants
from chatbridge.impl.cli import cli_client, cli_server
from chatbridge.impl.cqhttp import entry as cqhttp
from chatbridge.impl.discord import entry as discord
from chatbridge.impl.online import entry as online

__all__ = [
	'add_entry', 'main'
]


__ENTRY_MAPPING: Dict[str, Callable[[], Any]] = {
	'client': cli_client.main,
	'server': cli_server.main,
	'discord_bot': discord.main,
	'cqhttp_bot': cqhttp.main,
	'online_command': online.main,
}


def add_entry(arg: str, entry: Callable[[], Any]):
	__ENTRY_MAPPING[arg] = entry


def main():
	if len(sys.argv) == 2:
		arg = sys.argv[1]
		entry = __ENTRY_MAPPING.get(arg)
		if entry is not None:
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

