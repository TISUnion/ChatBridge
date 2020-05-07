# -*- coding: UTF-8 -*-
import copy
import os
import sys
import time
import json
import socket
try:
	from ChatBridgeLibrary import ChatBridge_lib as lib
	from ChatBridgeLibrary import ChatBridge_utils as utils
except ImportError: # as a MCD plugin
	sys.path.append("plugins/")
	from ChatBridgeLibrary import ChatBridge_lib as lib
	from ChatBridgeLibrary import ChatBridge_utils as utils

if os.path.isfile('plugins/StatsHelper.py'):
	sys.path.append("plugins/")
	import StatsHelper as stats
else:
	stats = None

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
	minecraftServer = None
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

	def start(self, minecraftServer=None):
		self.minecraftServer = minecraftServer
		if not self.isOnline():
			self.log('Trying to start the client, connecting to ' + utils.addressToString(self.server_addr))
			self.sock = socket.socket()
			# 发送客户端信息
			try:
				self.sock.connect(self.server_addr)
				self.send_login(self.info.name, self.info.password)
			except socket.error:
				self.log('Fail to connect to the server')
				return
			# 获取登录结果
			try:
				data = self.recieveData()
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

	def on_recieve_message(self, data):
		messages = utils.messageData_to_strings(data)
		for msg in messages:
			self.log(msg)
			if self.mode == Mode.MCD:
				msg = utils.stringAdd('§7', utils.stringAdd(msg, '§r'))
				self.minecraftServer.say(msg)

	def on_recieve_command(self, data):
		ret = copy.deepcopy(data)
		command = data['command']
		result = {'responded': True}
		global stats
		if command.startswith('!!stats '):
			if stats is not None:
				func = stats.onServerInfo if hasattr(stats, 'onServerInfo') else stats.on_info
				res_raw = func(None, None, command)
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

#  ----------------------
# | MCDaemon Part Start |
# ----------------------

def printLines(server, info, msg, isTell = True):
	for line in msg.splitlines():
		if info.isPlayer:
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

def onServerInfo(server, info):
	global client
	content = info.content
	if not info.isPlayer and content.endswith('<--[HERE]'):
		content = content.replace('<--[HERE]', '')
	command = content.split()
	if len(command) == 0 or command[0] != Prefix:
		setMinecraftServerAndStart(server)
		if info.isPlayer:
			client.log('Sending message "' + str((info.player, info.content)) + '" to the server')
			client.sendChatMessage(info.player, info.content)
		return
	del command[0]

	cmdLen = len(command)
	if cmdLen == 0:
		printLines(server, info, HelpMessage)
		return

	if cmdLen == 1 and command[0] == 'status':
		showClientStatus(server, info)
	elif cmdLen == 1 and command[0] == 'reload':
		stopClient(server, info)
		reloadClient()
		startClient(server, info)
	elif cmdLen == 1 and command[0] == 'start':
		startClient(server, info)
		showClientStatus(server, info)
	elif cmdLen == 1 and command[0] == 'stop':
		stopClient(server, info)
		showClientStatus(server, info)
	else:
		printLines(server, info, HelpMessage)


def onServerStartup(server):
	setMinecraftServerAndStart(server)


def onPlayerJoin(server, playername):
	setMinecraftServerAndStart(server)
	global client
	client.sendMessage(playername + ' joined ' + client.info.name)


def onPlayerLeave(server, playername):
	setMinecraftServerAndStart(server)
	global client
	client.sendMessage(playername + ' left ' + client.info.name)

#  --------------------
# | MCDaemon Part End |
# --------------------

#  ----------------------------
# | MCDReforged Compatibility |
# ----------------------------


def on_unload(server):
	global client
	if client is not None:
		client.stop()


def on_load(server, old):
	onServerStartup(server)
	server.add_help_message(Prefix, '跨服聊天控制')


def on_player_joined(server, playername):
	onPlayerJoin(server, playername)


def on_player_left(server, playername):
	onPlayerLeave(server, playername)


def on_info(server, info):
	info2 = copy.deepcopy(info)
	info2.isPlayer = info2.is_player
	onServerInfo(server, info2)


def on_death_message(server, message):
	setMinecraftServerAndStart(server)
	global client
	client.sendMessage(message)

#  -------------------------------
# | MCDReforged Compatibility End|
# -------------------------------


def reloadClient():
	global ConfigFile, LogFile, client, mode
	if mode == None:
		if __name__ == '__main__':
			mode = Mode.Client
		else:
			mode = Mode.MCD
			ConfigFile = 'config/' + ConfigFile
			LogFile = 'log/' + LogFile
	client = ChatClient(ConfigFile, LogFile, mode)


client = None
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
		msg = raw_input() if sys.version_info.major == 2 else input()
		if msg == 'stop':
			client.stop(True)
		elif msg == 'start':
			client.start(None)
		else:
			client.sendMessage(msg)
