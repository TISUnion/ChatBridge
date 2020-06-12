# -*- coding: UTF-8 -*-
import collections
import copy
import json
import threading
import time
import traceback

import ChatBridge_client
from ChatBridgeLibrary.rcon import Rcon
from ChatBridgeLibrary import ChatBridge_utils as utils

OnlineCommandConfigFile = 'ChatBridge_!!online.json'
ClientConfigFile = 'ChatBridge_client.json'
LogFile = 'ChatBridge.log'
cq_bot = None
chatClient = None


def log(msg):
	msg = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time())) + ' [CQBot] ' + str(msg)
	print(msg)
	utils.printLog(msg, LogFile)


class ChatClient(ChatBridge_client.ChatClient):
	def __init__(self, clientConfigFile):
		super(ChatClient, self).__init__(clientConfigFile, LogFile, 'Other')
		with open(OnlineCommandConfigFile, 'r') as f:
			self.query_list = json.load(f)

	def on_recieve_command(self, data):
		if data['command'] == '!!online' and not data['result']['responded']:
			result = {
				'responded': True,
				'type': 0,
				'result': query_online(self.query_list)
			}
			ret = copy.deepcopy(data)
			ret['result'] = result
			ret_str = json.dumps(ret)
			self.log('Sending respond {}'.format(ret_str))
			self.sendData(ret_str)

	def on_recieve_message(self, data):
		pass


def query_online(query_list):
	counter = collections.OrderedDict()
	for server in query_list:
		log('Querying bungeecord server "{}"'.format(server['name']))
		rcon = Rcon(server['address'], server['port'], server['password'])
		try:
			if not rcon.connect():
				continue
			respond = rcon.send_command('glist')
			if not respond:
				log('Rcon command not respond')
				continue
			log('Respond received: ')
			for line in respond.splitlines():
				log('    {}'.format(line))
				if not line.startswith('Total players online:'):
					server_name = line.split('] (', 1)[0][1:]
					player_list = set(line.split('): ')[-1].split(', '))
					if '' in player_list:
						player_list.remove('')
					if server_name not in counter:
						counter[server_name] = set()
					counter[server_name].update(player_list)
		except:
			traceback.print_exc()
		finally:
			rcon.disconnect()
	counter_sorted = sorted([(key, value) for key, value in counter.items()], key=lambda x: x[0].upper())
	player_set_all = set()
	res = 'Players in {} bungeecord servers: \n'.format(len(query_list))
	for server_name, player_set in counter_sorted:
		if player_set:
			player_set_all.update(player_set)
			res += '[{}] ({}): {}\n'.format(server_name, len(player_set), ', '.join(sorted(player_set, key=lambda x: x.upper())))
	res += 'Total players online: {}'.format(len(player_set_all))
	return res


def console_input():
	while True:
		try:
			text = input()
			if text == '!!online':
				global chatClient
				print(query_online(chatClient.query_list))
		except:
			traceback.print_exc()


if __name__ == '__main__':
	print('[ChatBridge] OnlineCommand Config File = ' + OnlineCommandConfigFile)
	print('[ChatBridge] ChatBridge Client Config File = ' + ClientConfigFile)

	chatClient = ChatClient(ClientConfigFile)
	thread = threading.Thread(target=console_input, args=())
	thread.setDaemon(True)
	thread.start()
	try:
		while True:
			if not chatClient.isOnline():
				chatClient.start()
			time.sleep(3)
	except (KeyboardInterrupt, SystemExit):
		chatClient.stop()
	print('Bye~')
