# -*- coding: UTF-8 -*-
import os
import json
import threading
import time
import traceback
import requests
import re
import ChatBridge_client
import websocket
from ChatBridgeLibrary import ChatBridge_lib as lib
from ChatBridgeLibrary import ChatBridge_utils as utils

CQHttpConfigFile = 'ChatBridge_CQHttp.json'
ClientConfigFile = 'ChatBridge_client.json'
LogFile = 'ChatBridge_CQHttp.log'
cq_bot = None
chatClient = None

CQHelpMessage = '''
!!help: 显示本条帮助信息
!!ping: pong!
!!online: 显示正版通道在线列表
!!stats <类别> <内容> [<-bot>]: 查询统计信息 <类别>.<内容> 的排名
'''.strip()
StatsHelpMessage = '''
!!stats <类别> <内容> [<-bot>]
添加 `-bot` 来列出 bot
例子:
!!stats used diamond_pickaxe
!!stats custom time_since_rest -bot
'''.strip()

def log(msg):
	msg = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time())) + ' [CQBot] ' + str(msg)
	print(msg)
	utils.printLog(msg, LogFile)


class CoolQConfig():
	def __init__(self, configFile):
		js = json.load(open(configFile, 'r'))
		self.ws_address = js['ws_address']
		self.ws_port = js['ws_port']
		self.access_token = js['access_token']
		self.react_group_id = js['react_group_id']
		self.client_to_query_stats = js['client_to_query_stats']
		self.client_to_query_online = js['client_to_query_online']
		self.prefix_mode = js['prefix_mode']
		log('Websocket address = {}'.format(self.ws_address))
		log('Websocket port = {}'.format(self.ws_port))
		log('Websocket access_token = {}'.format(self.access_token))
		log('Reacting QQ group id = {}'.format(self.react_group_id))
		log('Client to Query !!stats = ' + self.client_to_query_stats)
		log('Client to Query !!online = ' + self.client_to_query_online)
		log('Prefix Mode = {}'.format(self.prefix_mode))

class CQBot(websocket.WebSocketApp):
	def __init__(self, configFile):
		self.config = CoolQConfig(configFile)
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
			global prefix_mode
		#	log('Message received: ' + str(message))
			if chatClient is None:
				return
			data = json.loads(message)
			if 'status' in data:
				log('CoolQ return status {}'.format(data['status']))
			elif data['post_type'] == 'message' and data['message_type'] == 'group':
				if data['anonymous'] is None and data['group_id'] == self.config.react_group_id:
					args = data['raw_message'].split(' ')

					if len(args) == 1 and args[0] == '!!help':
						log('!!help command triggered')
						self.send_text(CQHelpMessage)

					elif len(args) == 1 and args[0] == '!!ping':
						log('!!ping command triggered')
						self.send_text('pong!')

					elif len(args) == 1 and args[0] == '!!online':
						log('!!online command triggered')
						if chatClient.isOnline:
							command = args[0]
							client = self.config.client_to_query_online
							log('Sending command "{}" to client {}'.format(command, client))
							chatClient.send_command_query(client, command)
						else:
							self.send_text('ChatBridge 客户端离线')

					elif len(args) >= 1 and args[0] == '!!stats':
						log('!!stats command triggered')
						command = '!!stats rank ' + ' '.join(args[1:])
						if len(args) == 0 or len(args) - int(command.find('-bot') != -1) != 3:
							self.send_text(StatsHelpMessage)
							return
						if chatClient.isOnline:
							client = self.config.client_to_query_stats
							log('Sending command "{}" to client {}'.format(command, client))
							chatClient.send_command_query(client, command)
						else:
							self.send_text('ChatBridge 客户端离线')

					else:
						sender = data['sender']['card']
						if len(sender) == 0:
							sender = data['sender']['nickname']
						if prefix_mode == "True":
							text = data['raw_message'].split(' ', 1)[1]
							qq_to_server(text, sender)
						else:
							text = data['raw_message']
							qq_to_server(text, sender, False)

		except:
			log('Error in on_message()')
			log(traceback.format_exc())

	def on_error(self, error):
		log(error)

	def on_close(self):
		log("Close connection")

	def _send_text(self, text):
		data = {
			"action": "send_group_msg",
			"params": {
				"group_id": self.config.react_group_id,
				"message": text
			}
		}
		self.send(json.dumps(data))

	def send_text(self, text):
		msg = ''
		length = 0
		lines = text.rstrip().splitlines(keepends=True)
		for i in range(len(lines)):
			msg += lines[i]
			length += len(lines[i])
			if i == len(lines) - 1 or length + len(lines[i + 1]) > 500:
				self._send_text(msg)
				msg = ''
				length = 0

	def send_message(self, client, player, message):
		self.send_text('[{}] <{}> {}'.format(client, player, message))


class ChatClient(ChatBridge_client.ChatClient):
	def __init__(self, clientConfigFile):
		super(ChatClient, self).__init__(clientConfigFile, LogFile, ChatBridge_client.Mode.CoolQ)

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
		result = data['result']
		if not result['responded']:
			return
		global cq_bot
		if data['command'].startswith('!!stats '):
			result_type = result['type']
			if result_type == 0:
				cq_bot.send_text('====== {} ======\n{}'.format(result['stats_name'], result['result']))
			elif result_type == 1:
				cq_bot.send_text('统计信息未找到')
			elif result_type == 2:
				cq_bot.send_text('StatsHelper 插件未加载')
		elif data['command'] == '!!online':
			result_type = result['type']
			if result_type == 0:
				cq_bot.send_text('====== 玩家列表 ======\n{}'.format(result['result']))
			elif result_type == 1:
				cq_bot.send_text('玩家列表查询失败')
			elif result_type == 2:
				cq_bot.send_text('Rcon 离线')


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

def qq_to_server(text, sender, prefix_mode=True):
	text = qq_text_process(text)
	log('Sending message {} to server...'.format(text))
	chatClient.sendChatMessage(sender, text)

def qq_text_process(text):
	temp = re.search('\[CQ:at,qq=.*\]', text)
	if temp is not None:
		temp = re.search('qq=.*[^/]]', temp.group()).group()[3:-1]
		if temp == 'all':
			temp = '[@ 全体成员]'
		else:
			temp = '[@ {}]'.format(get_qq_name(temp))
		text = re.sub('\[CQ:at.*\]', temp, text)
	if re.search('\[CQ:image.*\]', text) is not None:
		text = re.sub('\[CQ:image.*\]', '[图片]', text)
	if re.search('\[CQ:face.*\]', text) is not None:
		text = re.sub('\[CQ:face.*\]', '[表情]', text)
	if re.search('\[CQ:record.*\]', text) is not None:
		text = '[语音]'
	if re.search('\[CQ:.*\]', text) is not None:
		text = re.sub('\[CQ:.*\]', '[其他消息]', text)
	return text
	
def get_qq_name(qqid):
	print(qqid)
	temp = requests.get('https://users.qzone.qq.com/fcg-bin/cgi_get_portrait.fcg?uins={}'.format(qqid))
	temp_js = json.loads(temp.text[17:-1])
	return temp_js[qqid][6]
	
if __name__ == '__main__':
	prefix_mode = CoolQConfig(CQHttpConfigFile).prefix_mode
	print('[ChatBridge] CoolQ Config File = ' + CQHttpConfigFile)
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
