"""
A specific client for responding !!online command for multiple bungeecord instances
"""
import collections
import traceback
from typing import List

from mcdreforged.api.rcon import RconConnection

from chatbridge.core.client import ChatBridgeClient
from chatbridge.core.network.protocol import CommandPayload
from chatbridge.impl import utils
from chatbridge.impl.online.config import OnlineConfig
from chatbridge.impl.tis.protocol import OnlineQueryResult

ClientConfigFile = 'ChatBridge_!!online.json'
chatClient: 'OnlineChatClient'
config: OnlineConfig


class OnlineChatClient(ChatBridgeClient):
	def on_command(self, sender: str, payload: CommandPayload):
		if payload.command == '!!online':
			self.reply_command(sender, payload, OnlineQueryResult.create(self.query()))

	def query(self) -> List[str]:
		counter = collections.OrderedDict()
		for server in config.bungeecord_list:
			self.logger.info('Querying bungeecord server "{}"'.format(server.name))
			rcon = RconConnection(server.address, server.port, server.password)
			try:
				if not rcon.connect():
					continue
				respond = rcon.send_command('glist')
				if not respond:
					self.logger.warning('Rcon command not respond')
					continue
				self.logger.info('Respond received: ')
				for line in respond.splitlines():
					self.logger.info('    {}'.format(line))
					if not line.startswith('Total players online:'):
						server_name = line.split('] (', 1)[0][1:]
						player_list = set(line.split('): ')[-1].split(', '))
						if '' in player_list:
							player_list.remove('')
						if server_name not in counter:
							counter[server_name] = set()
						counter[server_name].update(player_list)
			except:
				self.logger.exception('Error when querying {}'.format(server.name))
			finally:
				rcon.disconnect()
		counter_sorted = sorted([(key, value) for key, value in counter.items()], key=lambda x: x[0].upper())
		player_set_all = set()
		result: List[str] = ['Players in {} bungeecord servers:'.format(len(config.bungeecord_list))]
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
		except:
			traceback.print_exc()


def main():
	global config, chatClient
	config = utils.load_config(ClientConfigFile, OnlineConfig)
	chatClient = OnlineChatClient.create(config)
	utils.start_guardian(chatClient)
	console_input_loop()


if __name__ == '__main__':
	main()
