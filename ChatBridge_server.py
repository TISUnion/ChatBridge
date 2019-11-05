# -*- coding: UTF-8 -*-

import os
import sys
import thread
import time
import json
import socket
import ChatBridge_lib

'''
数据包格式：
开始连接：
{
	"action": "start",
	"name": "ClientName",
	"password": "ClientPassword"
}
传输信息：
{
	"action": "message",
	"data": "MESSAGE_STRING"
}
结束连接：
{
	"action": "stop"
}
'''
ConfigFile = 'ChatBridge_server.json'

class ChatClient(ChatBridge_lib.ChatClient, object):
	def __init__(self, info, server, cryptorPassword):
		super(ChatClient, self).__init__(info, cryptorPassword)
		self.server = server

	def start(self, conn, addr):
		if self.online:
			self.log('stopping existing connection to start')
			try:
				self.stop(True)
			except socket.error:
				self.log('fail to stop existing connection, ignore that')
		self.conn, self.addr = conn, addr
		thread.start_new_thread(self.run, ())

	def run(self):
		self.log('client address = ' + str(self.addr))
		super(ChatClient, self).run()

	def recieveMessage(self, data):
		server.boardcastMessage(self.info, data)

	def sendMessage(self, msg):
		if self.online:
			self.log('sending message "' + msg + '" to the client')
		super(ChatClient, self).sendMessage(msg)


class ChatServer():
	def __init__(self, configFile):
		self.online = False
		config = json.load(open(configFile, 'r'))
		self.cryptorPassword = config['aes_key']
		self.AESCryptor = ChatBridge_lib.AESCryptor(self.cryptorPassword)
		self.server_addr = config['hostname'], config['port']
		self.log('cryptorPassword = ' + self.cryptorPassword)
		self.log('server address = ' + str(self.server_addr))
		self.clients = []
		for c in config['clients']:
			info = ChatBridge_lib.ChatClientInfo(c['name'], c['password'])
			self.log('Adding Client: name = ' + info.name + ', password = ' + info.password)
			self.clients.append(ChatClient(info, self, self.cryptorPassword))

	def log(self, msg):
		print '[ChatBridgeServer]', msg

	def __del__(self):
		if self.online:
			self.sock.close()
			self.log('Server Closed')

	def boardcastMessage(self, senderInfo, msg):
		self.log('revieved "' + msg + '" from ' + senderInfo.name + ', boardcasting')
		msg = '[' + senderInfo.name + '] ' + msg
		for i in range(len(self.clients)):
			if not self.clients[i].info == senderInfo:
				self.clients[i].sendMessage(msg)

	def run(self):
		self.sock = socket.socket()
		try:
			self.sock.bind(self.server_addr)
		except socket.error:
			self.log('fail to bind ' + str(self.server_addr))
			return False
		self.sock.listen(5)
		self.online = True
		self.log('Server Started')
		while self.online:
			conn, addr = self.sock.accept()
			self.log('Client ' + str(addr) + 'connected, recieving initializing data')
			try:
				js = json.loads(self.AESCryptor.decrypt(conn.recv(1024))) # 接受客户端信息的数据包
				self.log('initializing data =' + str(js))
				if js['action'] == 'start':
					info = ChatBridge_lib.ChatClientInfo(js['name'], js['password'])
					for i in range(len(self.clients)):
						if self.clients[i].info == info:
							self.clients[i].start(conn, addr)
							break
			except ValueError:
				self.log('fail to read received initializing json data')
			time.sleep(0.5)
		return True

if len(sys.argv) == 2:
	ConfigFile = sys.argv[1]
print 'Config File = ' + ConfigFile
if os.path.isfile(ConfigFile):
	server = ChatServer(ConfigFile)
	server.run()
else:
	print 'Config File not Found'
print 'Program exiting ...'
