# -*- coding: UTF-8 -*-

import os
import sys
import time
import json
import socket
import ChatBridge_lib

ConfigFile = 'ChatBridge_server.json'
GeneralLogFile = 'ChatBridge_server.log'
ChatLogFile = 'chat.log'

class ChatClient(ChatBridge_lib.ChatClient, object):
	def __init__(self, info, server, cryptorPassword):
		super(ChatClient, self).__init__(info, cryptorPassword, GeneralLogFile)
		self.server = server

	def start(self, conn, addr):
		if self.isOnline():
			self.log('Stopping existing connection to start')
			try:
				self.stop(True)
			except socket.error:
				self.log('Fail to stop existing connection, ignore that')
		self.conn, self.addr = conn, addr
		super(ChatClient, self).start()

	def run(self):
		self.log('Client address = ' + ChatBridge_lib.addressToString(self.addr))
		super(ChatClient, self).run()

	def recieveMessage(self, data):
		server.boardcastMessage(self.info, data)

	def sendMessage(self, msg):
		if self.isOnline():
			self.log('Sending message "' + msg + '" to the client')
		super(ChatClient, self).sendMessage(msg)


class ChatServer():
	def __init__(self, configFile):
		self.online = False
		config = json.load(open(configFile, 'r'))
		self.cryptorPassword = config['aes_key']
		self.AESCryptor = ChatBridge_lib.AESCryptor(self.cryptorPassword)
		self.server_addr = ChatBridge_lib.toUTF8(config['hostname']), config['port']
		self.log('CryptorPassword = ' + self.cryptorPassword)
		self.log('Server address = ' + ChatBridge_lib.addressToString(self.server_addr))
		self.clients = []
		for c in config['clients']:
			info = ChatBridge_lib.ChatClientInfo(c['name'], c['password'])
			self.log('Adding Client: name = {0}, password = {1}'.format(info.name, info.password))
			self.clients.append(ChatClient(info, self, self.cryptorPassword))
			self.clients.append(ChatClient(info, self, self.cryptorPassword))

	def log(self, msg):
		msg = ChatBridge_lib.stringAdd('[ChatBridgeServer] ', msg)
		print(msg)
		ChatBridge_lib.printLog(msg, GeneralLogFile)

	def isOnline(self):
		return self.online

	def sendData(self, conn, msg):
		conn.sendall(self.AESCryptor.encrypt(msg))

	def recieveData(self, conn):
		return self.AESCryptor.decrypt(conn.recv(1024))

	def boardcastMessage(self, senderInfo, msg):
		msg = ChatBridge_lib.toUTF8(msg)
		self.log('Revieved "{0}" from {1}, boardcasting'.format(msg, senderInfo.name))
		msg = '[' + senderInfo.name + '] ' + msg
		ChatBridge_lib.printLog(msg, ChatLogFile)
		for i in range(len(self.clients)):
			if not self.clients[i].info == senderInfo:
				self.clients[i].sendMessage(msg)

	def run(self):
		self.sock = socket.socket()
		try:
			self.sock.bind(self.server_addr)
		except socket.error, msg:
			self.log(str(msg))
			self.log('Fail to bind ' + str(self.server_addr))
			return False
		self.sock.listen(5)
		self.online = True
		self.log('Server Started')
		while self.isOnline():
			conn, addr = self.sock.accept()
			self.log('Client {0} connected, recieving initializing data'.format(ChatBridge_lib.addressToString(addr)))
			try:
				js = json.loads(self.AESCryptor.decrypt(conn.recv(1024))) # 接受客户端信息的数据包
				self.log('Initializing data =' + str(js))
				if js['action'] == 'start':
					info = ChatBridge_lib.ChatClientInfo(js['name'], js['password'])
					flag = False
					for i in range(len(self.clients)):
						if self.clients[i].info == info:
							self.sendData(conn, '{"action":"result","data":"login success"}')
							flag = True
							self.log('Starting client "' + self.clients[i].info.name + '"')
							self.clients[i].start(conn, addr)
							break
					if flag == False:
						conn.sendall(self.AESCryptor.encrypt('{"action":"result","data":"login fail"}'))
			except ValueError:
				self.log('Fail to read received initializing json data')
			except socket.error:
				self.log('Fail to respond the client')
			time.sleep(0.1)
		return True

	def stop(self):
		self.online = False
		for i in range(len(self.clients)):
			if self.clients[i].isOnline():
				self.clients[i].stop(True)
		self.sock.close()
		self.log('Server stopped')

if len(sys.argv) == 2:
	ConfigFile = sys.argv[1]
print('[ChatBridgeServer] Config File = ' + ConfigFile)
if os.path.isfile(ConfigFile):
	server = ChatServer(ConfigFile)
	try:
		server.run()
	except (KeyboardInterrupt, SystemExit):
		server.stop()
else:
	print('[ChatBridgeServer] Config File not Found')
print('[ChatBridgeServer] Program exiting ...')
