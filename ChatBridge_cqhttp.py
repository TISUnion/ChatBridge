# -*- coding: UTF-8 -*-
import os
import json
import threading
import time
import traceback

import ChatBridge_client
import websocket
from ChatBridgeLibrary import ChatBridge_lib as lib
from ChatBridgeLibrary import ChatBridge_utils as utils

CQHttpConfigFile = 'ChatBridge_CQHttp.json'
ClientConfigFile = 'ChatBridge_client.json'
LogFile = 'ChatBridge_CQHttp.log'
cq_bot = None
chatClient = None


def log(msg):
	msg = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time())) + ' [CQBot] ' + msg
	print(msg)
	utils.printLog(msg, LogFile)


class DiscordConfig():
	def __init__(self, configFile):
		js = json.load(open(configFile, 'r'))
		self.ws_address = js['ws_address']
		self.ws_port = js['ws_port']
		self.access_token = js['access_token']
		self.react_group_id = js['react_group_id']
		log('Websocket address = {}'.format(self.ws_address))
		log('Websocket port = {}'.format(self.ws_port))
		log('Websocket access_token = {}'.format(self.access_token))
		log('Reacting QQ group id = {}'.format(self.react_group_id))


class CQBot(websocket.WebSocketApp):
	def __init__(self, configFile):
		self.config = DiscordConfig(configFile)
		websocket.enableTrace(True)
		url = 'ws://{}:{}/'.format(self.config.ws_address, self.config.ws_port)
		if self.config.access_token is not None:
			url += '?access_token={}'.format(self.config.access_token)
		log('Connecting to {}'.format(url))
		super().__init__(url,  on_message=self.on_message, on_close=self.on_close, on_error=self.on_error)

	def start(self):
		self.run_forever()

	def on_message(self, message):
		try:
			global chatClient
			log('Message received: ' + str(message))
			if chatClient is None:
				return
			data = json.loads(message)
			if data['post_type'] == 'message' and data['message_type'] == 'group':
				if data['anonymous'] is None and data['group_id'] == self.config.react_group_id:
					sender = data['sender']['nickname']
					try:
						prefix, text = data['raw_message'].split(' ', 1)
					except:
						pass
					else:
						if prefix == '!!mc':
							chatClient.sendChatMessage(sender, text)
		except:
			log('Error in on_message()')
			log(traceback.format_exc())

	def on_error(self, error):
		log(error)

	def on_close(self):
		log("Close connection")

	def send_message(self, client, player, message):
		data = {
			"action": "send_group_msg",
			"params": {
				"group_id": self.config.react_group_id,
				"message": '[{}] <{}> {}'.format(client, player, message)
			}
		}
		self.send(json.dumps(data))


class ChatClient(ChatBridge_client.ChatClient):
	def __init__(self, clientConfigFile):
		super(ChatClient, self).__init__(clientConfigFile, LogFile, ChatBridge_client.Mode.Discord)

	def on_recieve_message(self, data):
		global cq_bot
		if cq_bot is None:
			return
		try:
			messages = utils.messageData_to_strings(data)
			for msg in messages:
				self.log(msg)
			try:
				prefix, message = data['message'].split(' ', 1)
			except:
				pass
			else:
				log('Triggered command, sending message to qq')
				if prefix == '!!qq':
					cq_bot.send_message(data['client'], data['player'], message)
		except:
			self.log('Error in on_message()')
			self.log(traceback.format_exc())

	def on_recieve_command(self, data):
		pass


def ChatBridge_guardian():
	global chatClient,cq_bot
	chatClient = ChatClient(ClientConfigFile)
	time.sleep(3)
	try:
		while True:
			if not chatClient.isOnline():
				chatClient.start()
			time.sleep(3)
	except (KeyboardInterrupt, SystemExit):
		chatClient.stop()
		exit(1)


if __name__ == '__main__':
	print('[ChatBridge] Discord Config File = ' + CQHttpConfigFile)
	print('[ChatBridge] ChatBridge Client Config File = ' + ClientConfigFile)
	if not os.path.isfile(CQHttpConfigFile) or not os.path.isfile(ClientConfigFile):
		print('[ChatBridge] Config File missing, exiting')
		exit(1)

	thread = threading.Thread(target=ChatBridge_guardian, args=())
	thread.setDaemon(True)
	thread.start()
	cq_bot = CQBot(CQHttpConfigFile)
	cq_bot.start()
	print('Bye~')
