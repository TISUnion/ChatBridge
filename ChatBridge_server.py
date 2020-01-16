# -*- coding: UTF-8 -*-

import os
import sys
import time
import json
import socket
from ChatBridgeLibrary import ChatBridge_lib as lib
from ChatBridgeLibrary import ChatBridge_utils as utils

ConfigFile = 'ChatBridge_server.json'
GeneralLogFile = 'ChatBridge_server.log'
ChatLogFile = 'chat.log'

class ChatClient(lib.ChatClientBase):
	def __init__(self, info, server, AESKey):
		super(ChatClient, self).__init__(info, AESKey, GeneralLogFile)
		self.server = server

	def tryStart(self, conn, addr):
		if self.isOnline():
			self.log('Stopping existing connection to start')
			try:
				self.stop()
			except socket.error:
				self.log('Fail to stop existing connection, ignoring that')
			time.sleep(1)
		self.sock, self.addr = conn, addr
		super(ChatClient, self).start()

	def run(self):
		self.log('Client address = ' + utils.addressToString(self.addr))
		super(ChatClient, self).run()

	def on_recieve_message(self, data):
		server.boardcastMessage(self.info, data)

	def on_recieve_command(self, data):
		server.transitCommand(self.info, data)

	def sendMessage(self, messageData):
		if self.isOnline():
			self.log('Sending message "{}" to the client'.format(utils.lengthLimit(utils.messageData_to_string(messageData))))
			self.sendData(json.dumps(messageData))

	def sendCommand(self, commandData):
		if self.isOnline():
			self.log('Sending command "{}" to the client'.format(utils.lengthLimit(utils.commandData_to_string(commandData))))
			self.sendData(json.dumps(commandData))


class ChatServer(lib.ChatBridgeBase):
	def __init__(self, configFile):
		config = json.load(open(configFile, 'r'))
		super(ChatServer, self).__init__('Server', GeneralLogFile, config['aes_key'])
		self.server_addr = utils.toUTF8(config['hostname']), config['port']
		self.log('AESKey = ' + self.AESKey)
		self.log('Server address = ' + utils.addressToString(self.server_addr))
		self.clients = []
		for c in config['clients']:
			info = lib.ChatClientInfo(c['name'], c['password'])
			self.log('Adding Client: name = {0}, password = {1}'.format(info.name, info.password))
			self.clients.append(ChatClient(info, self, self.AESKey))

	def boardcastMessage(self, senderInfo, messageData):
		self.log('Received message "{0}", boardcasting'.format(utils.messageData_to_string(messageData)))
		for msg in utils.messageData_to_strings(messageData):
			self.log(msg, ChatLogFile)
		for client in self.clients:
			if client.info != senderInfo:
				client.sendMessage(messageData)

	def transitCommand(self, senderInfo, commandData):
		self.log('Received command "{0}", transiting'.format(utils.commandData_to_string(commandData)))
		target = commandData['sender'] if commandData['result']['responded'] else commandData['receiver']
		for client in self.clients:
			if client.info != senderInfo and client.info.name == target:
				client.sendCommand(commandData)

	def run(self):
		self.sock = socket.socket()
		try:
			self.sock.bind(self.server_addr)
		except socket.error:
			self.log('Fail to bind ' + str(self.server_addr))
			return False
		self.sock.listen(5)
		self.online = True
		self.log('Server Started')
		while self.isOnline():
			conn, addr = self.sock.accept()
			self.log('Client {0} connected, receiving initializing data'.format(utils.addressToString(addr)))
			try:
				js = json.loads(self.recieveData(conn)) # 接受客户端信息的数据包
				self.log('Initializing data =' + str(js))
				if js['action'] == 'login':
					info = lib.ChatClientInfo(js['name'], js['password'])
					flag = False
					for client in self.clients:
						if client.info == info:
							self.send_result('login success', conn)
							flag = True
							self.log('Starting client "' + client.info.name + '"')
							client.tryStart(conn, addr)
							break
					if flag == False:
						self.send_result('login fail', conn)
				else:
					self.log('Action not matches, ignore')
			except (ValueError, TypeError, KeyError) as err:
				self.log('Fail to read received initializing json data: ' + str(err))
			except socket.error:
				self.log('Fail to respond the client')
			utils.sleep()
		return True

	def stop(self):
		self.online = False
		for i in range(len(self.clients)):
			if self.clients[i].isOnline():
				self.clients[i].stop()
		self.sock.close()
		self.log('Server stopped')


if len(sys.argv) == 2:
	ConfigFile = sys.argv[1]
print('[ChatBridge] Config File = ' + ConfigFile)
if os.path.isfile(ConfigFile):
	server = ChatServer(ConfigFile)
	try:
		server.run()
	except (KeyboardInterrupt, SystemExit):
		server.stop()
else:
	print('[ChatBridge] Config File not Found')
print('[ChatBridge] Program exiting ...')
