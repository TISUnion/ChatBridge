"""
A specific client for responding !!online command for multiple bungeecord instances
"""
import collections
import functools
import re
import sys
import traceback
from concurrent.futures.thread import ThreadPoolExecutor
from threading import Lock
from typing import List, Dict, Set, Callable, Collection, Any, Tuple

import parse
from mcdreforged.api.rcon import RconConnection

from chatbridge.core.client import ChatBridgeClient
from chatbridge.core.network.protocol import CommandPayload
from chatbridge.impl import utils
from chatbridge.impl.online.config import OnlineConfig, RconEntry
from chatbridge.impl.tis.protocol import OnlineQueryResult

ClientConfigFile = 'ChatBridge_!!online.json'
chatClient: 'OnlineChatClient'
config: OnlineConfig


class OnlineChatClient(ChatBridgeClient):
	def on_command(self, sender: str, payload: CommandPayload):
		if payload.command == '!!online':
			self.reply_command(sender, payload, OnlineQueryResult.create(self.query()))

	def query_server(self, server: RconEntry, command: str, result_handler: Callable[[str], Any]):
		rcon = RconConnection(server.address, server.port, server.password)
		try:
			if not rcon.connect():
				return
			respond = rcon.send_command(command)
			if not respond:
				self.logger.warning('Rcon command not respond')
				return
			self.logger.info('Respond received from {}: {}'.format(server.name, repr(respond)))
			result_handler(respond)
		except:
			self.logger.exception('Error when querying {}'.format(server.name))
		finally:
			rcon.disconnect()

	@staticmethod
	def handle_minecraft(updater: Callable[[str, Collection[str]], Any], server: RconEntry, respond: str):
		formatters = (
			r'There are {amount:d} of a max {limit:d} players online:{players}',  # <1.16
			r'There are {amount:d} of a max of {limit:d} players online:{players}',  # >=1.16
		)
		for formatter in formatters:
			parsed = parse.parse(formatter, respond)
			if parsed is not None and parsed['players'].startswith(' '):
				players = parsed['players'][1:]
				if len(players) > 0:
					updater(server.name, players.split(', '))
				else:
					updater(server.name, ())
				break

	@staticmethod
	def handle_bungee(updater: Callable[[str, Collection[str]], Any], respond: str):
		for line in respond.splitlines():
			matched = re.fullmatch(r'\[([^]]+)] \(\d+\): (.*)', line)
			if matched:
				server_name = matched.group(1)
				player_list = set(filter(None, matched.group(2).split(', ')))
				updater(server_name, player_list)

	@staticmethod
	def server_comparator(item_a: Tuple[str, Any], item_b: Tuple[str, Any]) -> int:
		def get_index(name: str) -> int:
			try:
				return config.display_order.index(name)
			except ValueError:
				return len(config.display_order)

		name_a: str = item_a[0]
		name_b: str = item_b[0]
		order_a = get_index(name_a)
		order_b = get_index(name_b)
		if order_a > order_b:
			return 1
		elif order_a < order_b:
			return -1
		else:
			return int(name_a.upper() > name_b.upper()) - int(name_a.upper() < name_b.upper())

	def query(self) -> List[str]:
		def updater(name: str, players: Collection[str]):
			with lock:
				counter[name].update(players)
		counter: Dict[str, Set[str]] = collections.defaultdict(set)
		lock = Lock()
		with ThreadPoolExecutor() as pool:
			for server in config.server_list:
				pool.submit(self.query_server, server, 'list', lambda data, svr=server: self.handle_minecraft(updater, svr, data))
			for server in config.bungeecord_list:
				pool.submit(self.query_server, server, 'glist all', lambda data: self.handle_bungee(updater, data))

		counter_sorted = sorted([(key, value) for key, value in counter.items()], key=functools.cmp_to_key(self.server_comparator))
		player_set_all = set()
		result: List[str] = ['Players in {} Minecraft servers:'.format(len(list(filter(lambda i: i[1], counter_sorted))))]
		for server_name, player_set in counter_sorted:
			if player_set:
				player_set_all.update(player_set)
				result.append('[{}] ({}): {}'.format(server_name, len(player_set), ', '.join(sorted(player_set, key=lambda x: x.upper()))))
		result.append('Total players online: {}'.format(len(player_set_all)))
		return result


def console_input_loop():
	while True:
		try:
			text = input()
			if text in ['!!online', 'online']:
				print('\n'.join(chatClient.query()))
			elif text == 'stop':
				chatClient.stop()
				break
			else:
				print('online: show online status')
				print('stop: stop the client')
		except (KeyboardInterrupt, EOFError):
			print('Interrupted')
			break
		except:
			traceback.print_exc()


def main():
	global config, chatClient
	config = utils.load_config(ClientConfigFile, OnlineConfig)
	chatClient = OnlineChatClient.create(config)
	utils.start_guardian(chatClient)
	if sys.stdin.isatty():
		console_input_loop()
	else:
		utils.wait_until_terminate()
		chatClient.stop()


if __name__ == '__main__':
	main()
