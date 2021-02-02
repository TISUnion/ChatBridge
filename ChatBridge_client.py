# -*- coding: UTF-8 -*-
import copy
import json
import os
import socket
import sys
import time
from threading import Lock
from typing import Optional

try:
	from ChatBridgeLibrary import ChatBridge_lib as lib
	from ChatBridgeLibrary import ChatBridge_utils as utils
except ImportError: # as a MCD plugin
	sys.path.append("plugins/")
	from ChatBridgeLibrary import ChatBridge_lib as lib
	from ChatBridgeLibrary import ChatBridge_utils as utils
Prefix = '!!ChatBridge'
ConfigFile = 'ChatBridge_client.json'
LogFile = 'ChatBridge_client.log'
HelpMessage = '''------MCD ChatBridge插件 v0.1------
一个跨服聊天客户端插件
§a【格式说明】§r
§7''' + Prefix + '''§r 显示帮助信息
§7''' + Prefix + ''' status§r 显示ChatBridge客户端状态
§7''' + Prefix + ''' reload§r 重新加载ChatBridge客户端配置文件
§7''' + Prefix + ''' start§r 开启ChatBridge客户端状态
§7''' + Prefix + ''' stop§r 关闭ChatBridge客户端状态
'''

class Mode():
	Client = 'Client'
	MCD = 'MCD'
	Discord = 'Discord'
	CoolQ = 'CoolQ'


class ChatClient(lib.ChatClientBase):
	def __init__(self, configFile, LogFile, mode):
		js = json.load(open(configFile, 'r'))
		super(ChatClient, self).__init__(lib.ChatClientInfo(js['name'], js['password']), js['aes_key'], LogFile)
		self.mode = mode
		self.consoleOutput = mode != Mode.MCD
		self.server_addr = (js['server_hostname'], js['server_port'])
		self.log('Client Info: name = ' + self.info.name + ', password = ' + self.info.password)
		self.log('Mode = ' + mode)
		self.log('AESKey = ' + self.AESKey)
		self.log('Server address = ' + utils.addressToString(self.server_addr))
		self.minecraftServer = None
		self.start_lock = Lock()

	def start(self, minecraftServer=None):
		acq = self.start_lock.acquire(False)
		if not acq:
			return
		try:
			self.minecraftServer = minecraftServer
			if not self.isOnline():
				self.log('Trying to start the client, connecting to ' + utils.addressToString(self.server_addr))
				self.sock = socket.socket()
				# 发送客户端信息
				try:
					self.sock.settimeout(5)
					self.sock.connect(self.server_addr)
					self.send_login(self.info.name, self.info.password)
				except socket.error:
					self.log('Fail to connect to the server')
					return
				# 获取登录结果
				try:
					data = self.recieveData(timeout=5)
					result = json.loads(data)['result']
				except socket.error:
					self.log('Fail to receive login result')
					return
				except ValueError:
					self.log('Fail to read login result')
					return
				self.log(utils.stringAdd('Result: ', result))
				if result == 'login success':
					super(ChatClient, self).start()
			else:
				self.log('Client has already been started')
		finally:
			self.start_lock.release()

	def on_recieve_message(self, data):
		messages = utils.messageData_to_strings(data)
		for msg in messages:
			self.log(msg)
			if self.mode == Mode.MCD:
				self.minecraftServer.execute('tellraw @a {}'.format(json.dumps({
					'text': msg,
					'color': 'gray'
				})))

	def on_recieve_command(self, data):
		ret = copy.deepcopy(data)
		command = data['command']  # type: str
		result = {'responded': True}
		if command.startswith('!!stats '):
			stats = None
			if self.mode == Mode.MCD:
				stats = self.minecraftServer.get_plugin_instance('stats_helper')  # MCDR 1.0+
			if stats is not None:
				trimmed_command = command.replace('-bot', '').replace('-all', '')
				try:
					prefix, typ, cls, target = trimmed_command.split()
					assert typ == 'rank' and type(target) is str
				except:
					res_raw = None
				else:
					res_raw = stats.show_rank(None, None, cls, target, '-bot' in command, False, '-all' in command, True)
				if res_raw is not None:
					lines = res_raw.splitlines()
					stats_name = lines[0]
					res = '\n'.join(lines[1:])
					result['type'] = 0
					result['stats_name'] = stats_name
					result['result'] = res
				else:
					result['type'] = 1
			else:
				result['type'] = 2
		elif command == '!!online':  # MCDR -> bungeecord rcon
			if self.minecraftServer is not None and hasattr(self.minecraftServer, 'MCDR') and self.minecraftServer.is_rcon_running():
				res = self.minecraftServer.rcon_query('glist')
				if res != None:
					result['type'] = 0
					result['result'] = res
				else:
					result['type'] = 1
			else:
				result['type'] = 2
		ret['result'] = result
		ret_str = json.dumps(ret)
		self.log('Command received, responding {}'.format(ret_str))
		self.sendData(ret_str)

	def sendChatMessage(self, player, message):
		self.log('Sending chat message "' + str((player, message)) + '" to the server')
		self.send_message(self.info.name, player, message)

	def sendMessage(self, message):
		self.log('Sending message "' + message + '" to the server')
		self.send_message(self.info.name, '', message)

#  ------------------
# | MCDR Part Start |
# ------------------

PLUGIN_METADATA = {
	'id': 'chatbridge_client',
	'version': '1.0.1',
	'name': 'ChatBridge_client',
	'author': 'Fallen_Breath',
	'link': 'https://github.com/TISUnion/ChatBridge',
	# 'dependencies': {
	# 	'mcdreforged': '>=1.0.2'
	# }
}


def thread_spam(func):
	# import here to avoid dependency restriction outside MCDR
	# only works for MCDR 1.0+
	from mcdreforged.api.decorator import new_thread
	return new_thread('ChatBridge')(func)


def printLines(server, info, msg, isTell = True):
	for line in msg.splitlines():
		if info.is_player:
			if isTell:
				server.tell(info.player, line)
			else:
				server.say(line)
		else:
			print(line)

def setMinecraftServerAndStart(server):
	global client
	if client == None:
		reloadClient()
	if not client.isOnline():
		client.start(server)

def startClient(server, info):
	printLines(server, info, '正在开启ChatBridge客户端')
	setMinecraftServerAndStart(server)
	time.sleep(1)

def stopClient(server, info):
	printLines(server, info, '正在关闭ChatBridge客户端')
	global client
	if client == None:
		reloadClient()
	client.stop(True)
	time.sleep(1)


def showClientStatus(server, info):
	global client
	printLines(server, info, 'ChatBridge客户端在线情况: ' + str(client.isOnline()))


def on_user_info(server, info):
	global client
	content = info.content
	command = content.split()
	if len(command) == 0 or command[0] != Prefix:
		if info.is_player:
			@thread_spam
			def sending():
				setMinecraftServerAndStart(server)
				client.log('Sending message "' + str((info.player, info.content)) + '" to the server')
				client.sendChatMessage(info.player, info.content)
			sending()
		return
	del command[0]

	cmdLen = len(command)

	@thread_spam
	def processInfo():
		if cmdLen == 0:
			printLines(server, info, HelpMessage)
			return

		if cmdLen == 1 and command[0] == 'status':
			showClientStatus(server, info)
		elif cmdLen == 1 and command[0] == 'reload':
			stopClient(server, info)
			reloadClient()
			startClient(server, info)
			showClientStatus(server, info)
		elif cmdLen == 1 and command[0] == 'start':
			startClient(server, info)
			showClientStatus(server, info)
		elif cmdLen == 1 and command[0] == 'stop':
			stopClient(server, info)
			showClientStatus(server, info)
		else:
			printLines(server, info, HelpMessage)

	processInfo()


def threadedSendMessage(message: str):
	@thread_spam
	def inner():
		global client
		client.sendMessage(message)
	inner()


def on_player_joined(server, playername, info):
	threadedSendMessage(playername + ' joined ' + client.info.name)


def on_player_left(server, playername):
	threadedSendMessage(playername + ' left ' + client.info.name)


def on_load(server, old):
	server.register_help_message(Prefix, '跨服聊天控制')
	setMinecraftServerAndStart(server)


# only in MCDR 0.x
def on_death_message(server, message):
	global client
	client.sendMessage(message)


def on_server_startup(server):
	threadedSendMessage('Server has started up')


def on_server_stop(server, return_code):
	threadedSendMessage('Server stopped')


def _stop():
	@thread_spam
	def inner():
		global client
		if client is not None:
			client.stop()
	inner()


def on_unload(server):
	_stop()


def on_remove(server):
	_stop()


def on_mcdr_stop(server):
	_stop()

#  -------------------------
# | MCDR Compatibility End |
# -------------------------


def reloadClient():
	global ConfigFile, LogFile, client, mode
	if mode is None:
		if __name__ == '__main__':
			mode = Mode.Client
		else:
			mode = Mode.MCD
			ConfigFile = 'config/' + ConfigFile
			LogFile = 'logs/' + LogFile
	client = ChatClient(ConfigFile, LogFile, mode)


client = None  # type: Optional[ChatClient]
mode = None

if __name__ == '__main__':
	mode = Mode.Client
	print('[ChatBridge] Config File = ' + ConfigFile)
	if not os.path.isfile(ConfigFile):
		print('[ChatBridge] Config File not Found, exiting')
		exit(1)

if mode == Mode.Client:
	reloadClient()
	client.start(None)
	while True:
		# noinspection PyUnresolvedReferences
		msg = raw_input() if sys.version_info.major == 2 else input()
		if msg == 'stop':
			client.stop(True)
		elif msg == 'start':
			client.start(None)
		else:
			client.sendMessage(msg)
