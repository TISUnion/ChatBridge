# -*- coding: UTF-8 -*-

import os
import sys
import threading
import time
import json
import socket
import traceback

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
		self.server.boardcastMessage(self.info, data)

	def on_recieve_command(self, data):
		self.server.transitCommand(self.info, data)

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
		self.start_console_thread()
		try:
			while self.isOnline():
				conn, addr = self.sock.accept()
				self.handle_client_connection(conn, addr)
				self.log('Client {0} connected, receiving initializing data'.format(utils.addressToString(addr)))
				utils.sleep()
		except:
			if self.isOnline():
				raise
		return True

	def handle_client_connection(self, conn, addr):
		try:
			js = json.loads(self.recieveData(conn))  # 接受客户端信息的数据包
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

	def stop(self):
		self.log('Server is stoppping')
		self.online = False
		for client in self.clients:
			if client.isOnline():
				client.stop()
		self.sock.close()
		self.log('Server stopped')

	def console_loop(self):
		while self.isOnline():
			# noinspection PyUnresolvedReferences
			text = raw_input() if sys.version_info.major == 2 else input()
			self.log('Processing user input "{}"'.format(text))
			if text == 'stop':
				self.stop()
			elif text.startswith('stop') and text.find(' ') != -1:
				target_name = text.split(' ', 1)[1]
				for client in self.clients:
					if client.info.name == target_name:
						self.log('Stopping client {}'.format(target_name))
						try:
							client.stop()
						except:
							traceback.print_exc()
						break
				else:
					self.log('Client {} not found'.format(target_name))
			elif text == 'list':
				self.log('client count: {}'.format(len(self.clients)))
				for client in self.clients:
					self.log('- {}: online = {}'.format(client.info.name, client.isOnline()))
			else:
				print('''
Type "stop" to stop the server
Type "stop client_name" to stop a client
Type "list" to show the client list
				'''.strip())

	def start_console_thread(self):
		console_thread = threading.Thread(target=self.console_loop)
		console_thread.setDaemon(True)
		console_thread.start()


def main():
	global ConfigFile
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


if __name__ == '__main__':
	main()
