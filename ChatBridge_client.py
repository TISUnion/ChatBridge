# -*- coding: UTF-8 -*-

import os
import sys
import imp
import time
import json
import socket
if os.path.isfile('plugins/ChatBridge_lib.py'): imp.load_source('ChatBridge_lib','plugins/ChatBridge_lib.py')
import ChatBridge_lib

Prefix = '!!ChatBridge'
ConfigFile = 'config/ChatBridge_client.json'
LogFile = 'log/ChatBridge_client.log'
HelpMessage = '''------MCD ChatBridge插件 v20191105------
一个跨服聊天客户端插件
§a【格式说明】§r
§7''' + Prefix + '''§r 显示帮助信息
§7''' + Prefix + ''' status§r 显示ChatBridge客户端状态
§7''' + Prefix + ''' reload§r 重新加载ChatBridge客户端配置文件
§7''' + Prefix + ''' start§r 开启ChatBridge客户端状态
§7''' + Prefix + ''' stop§r 关闭ChatBridge客户端状态
'''
class Mode():
	Client = 0
	MCD = 1

class ChatClient(ChatBridge_lib.ChatClient, object):
	minecraftServer = None
	def __init__(self, configFile):
		js = json.load(open(configFile, 'r'))
		super(ChatClient, self).__init__(ChatBridge_lib.ChatClientInfo(js['name'], js['password']), js['aes_key'], LogFile)
		global mode
		self.consoleOutput = mode != Mode.MCD
		self.server_addr = (js['server_hostname'], js['server_port'])
		self.color = js['color'] if 'color' in js else ''
		self.log('Client Info: name = ' + self.info.name + ', password = ' + self.info.password)
		self.log('cryptorPassword = ' + self.cryptorPassword)
		self.log('server address = ' + str(self.server_addr))

	def start(self, minecraftServer):
		self.minecraftServer = minecraftServer
		if not self.isOnline():
			self.log('trying to start the client, connecting to ' + str(self.server_addr))
			self.conn = socket.socket()
			try:
				self.conn.connect(self.server_addr)
				self.sendData(
					'{"action": "start","name":"' + self.info.name + '","password":"' + self.info.password + '"}')
			except socket.error:
				self.log('fail to connect to the server')
				return
			try:
				result = json.loads(self.recieveData())['data']
			except socket.error:
				self.log('fail to receive login result')
				return
			except ValueError:
				self.log('fail to read login result')
				return
			self.log(result)
			if result == 'login success':
				super(ChatClient, self).start()
		else:
			self.log('client has already been started')

	def sendMessage(self, msg):
		if self.isOnline():
			self.log('sending "' + msg + '" to server')
			js = {'action': 'message', 'data': msg}
			self.sendData(json.dumps(js))
			return True
		else:
			return False

	def recieveMessage(self, msg):
		global mode
		if type(msg).__name__ == 'unicode':
			msg = msg.encode('utf-8')
		if mode == Mode.Client:
			self.log(msg)
		elif mode == Mode.MCD:
			msg = self.color.encode('utf-8') + msg + '§r'
			self.minecraftServer.say(msg)

def printMessage(server, info, msg, isTell = True):
	for line in msg.splitlines():
		if info.isPlayer:
			if isTell:
				server.tell(info.player, line)
			else:
				server.say(line)
		else:
			print line

def startClient(server, info):
	printMessage(server, info, '正在开启ChatBridge客户端')
	setMinecraftServerAndStart(server)
	time.sleep(1)

def stopClient(server, info):
	printMessage(server, info, '正在关闭ChatBridge客户端')
	client.stop(True)
	time.sleep(1)

def reloadClient():
	global ConfigFile, client
	client = ChatClient(ConfigFile)

def showClientStatus(server, info):
	printMessage(server, info, 'ChatBridge客户端在线情况: ' + str(client.isOnline()))


def onServerInfo(server, info):
	global client
	content = info.content
	if not info.isPlayer and content.endswith('<--[HERE]'):
		content = content.replace('<--[HERE]', '')
	command = content.split()
	if command[0] != Prefix:
		if info.isPlayer:
			setMinecraftServerAndStart(server)
			client.sendMessage('<' + info.player + '> ' + info.content)
		return
	del command[0]

	cmdLen = len(command)
	if cmdLen == 0:
		printMessage(server, info, HelpMessage)
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
		printMessage(server, info, HelpMessage)

def setMinecraftServerAndStart(server):
	global client
	if not client.isOnline():
		client.start(server)

def onServerStartup(server):
	setMinecraftServerAndStart(server)

def onPlayerJoin(server, playername):
	setMinecraftServerAndStart(server)
	client.sendMessage(playername + ' joined ' + client.info.name)

def onPlayerLeave(server, playername):
	setMinecraftServerAndStart(server)
	client.sendMessage(playername + ' left ' + client.info.name)


if len(sys.argv) == 2:
	ConfigFile = sys.argv[1]
print '[ChatBridge] Config File = ' + ConfigFile
if not os.path.isfile(ConfigFile):
	print '[ChatBridge] Config File not Found, exiting'

if __name__ == '__main__':
	mode = Mode.Client
else:
	mode = Mode.MCD
print '[ChatBridge] mode =', {Mode.Client: 'Client', Mode.MCD: 'MCD'}[mode]

time.sleep(1)
reloadClient()
if mode == Mode.Client:
	client.start(None)
	while True:
		msg = raw_input()
		if msg == 'stop':
			client.stop(True)
		elif msg == 'start':
			client.start(None)
		else:
			client.sendMessage(msg)
