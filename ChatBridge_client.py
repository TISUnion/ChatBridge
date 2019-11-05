# -*- coding: UTF-8 -*-

import os
import sys
import thread
import imp
import json
import socket
if os.path.isfile('plugins/ChatBridge_lib.py'): imp.load_source('ChatBridge_lib','plugins/ChatBridge_lib.py')
import ChatBridge_lib

Prefix = '!!ChatBridge'
ConfigFile = 'ChatBridge_client.json'
HelpMessage = '''------MCD ChatBridge插件 v1.0------
一个跨服聊天客户端插件
'''
class Mode():
	Client = 0
	MCD = 1

class ChatClient(ChatBridge_lib.ChatClient, object):
	minecraftServer = None
	def __init__(self, configFile):
		js = json.load(open(configFile, 'r'))
		super(ChatClient, self).__init__(ChatBridge_lib.ChatClientInfo(js['name'], js['password']), js['aes_key'])
		self.server_addr = (js['server_hostname'], js['server_port'])
		self.log('Client Info: name = ' + self.info.name + ', password = ' + self.info.password)
		self.log('cryptorPassword = ' + self.cryptorPassword)
		self.log('server address = ' + str(self.server_addr))

	def start(self, minecraftServer):
		self.minecraftServer = minecraftServer
		if not self.online:
			self.log('trying to start the client, connecting to ' + str(self.server_addr))
			self.conn = socket.socket()
			try:
				self.conn.connect(self.server_addr)
				self.conn.sendall(self.AESCryptor.encrypt('{"action": "start","name":"' + self.info.name + '","password":"' + self.info.password + '"}'))
			except socket.error:
				self.log('fail to connect to the server')
				return
			thread.start_new_thread(self.run, ())
		else:
			self.log('client has already been started')

	def sendMessage(self, msg):
		if self.online:
			self.log('sending "' + msg + '" to server')
			js = {'action': 'message', 'data': msg}
			self.conn.sendall(self.AESCryptor.encrypt(json.dumps(js)))
			return True
		else:
			return False

	def recieveMessage(self, msg):
		global mode
		if type(msg).__name__=='unicode':
			msg = msg.encode('utf-8')
		if mode == Mode.Client:
			self.log(msg)
		elif mode == Mode.MCD:
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

def onServerInfo(server, info):
	global client
	if info.isPlayer:
		setMinecraftServerAndStart(server)
		client.sendMessage('<' + info.player + '> ' + info.content)

	content = info.content
	if not info.isPlayer and content.endswith('<--[HERE]'):
		content = content.replace('<--[HERE]', '')

	command = content.split()
	if command[0] != Prefix:
		return
	del command[0]

	cmdLen = len(command)
	if cmdLen == 0:
		printMessage(server, info, HelpMessage)
		return

	if cmdLen == 1 and command[0] == 'start':
		setMinecraftServerAndStart(server)

def setMinecraftServerAndStart(server):
	global client
	if not client.online:
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
print 'Config File = ' + ConfigFile
if not os.path.isfile(ConfigFile):
	print 'Config File not Found, exiting'
global client, mode
client = ChatClient(ConfigFile)

if __name__ == '__main__':
	mode = Mode.Client
	client.start(None)
	while True:
		msg = raw_input()
		if msg == 'stop':
			client.stop(True)
		elif msg == 'start':
			client.start(None)
		else:
			client.sendMessage(msg)
else:
	mode = Mode.MCD
