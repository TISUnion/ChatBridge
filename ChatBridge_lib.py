# coding: utf8

from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import json
import socket
import time

class ChatClientInfo():
	def __init__(self, name, password):
		self.name = name
		self.password = password

	def __eq__(self, other):
		return self.name == other.name and self.password == other.password


class ChatClient():
	conn = None

	def __init__(self, info, cryptorPassword):
		self.online = False
		self.info = info
		self.cryptorPassword = cryptorPassword
		self.AESCryptor = AESCryptor(self.cryptorPassword)

	def __del__(self):
		if self.online:
			self.conn.close()

	def log(self, msg):
		print '[ChatBridgeClient.' + self.info.name + ']', msg

	def stop(self, notifyConnection):
		if not self.online:
			self.log('cannot stop an offline client')
			return
		if notifyConnection:
			self.conn.sendall(self.AESCryptor.encrypt('{"action": "stop"}'))
		self.conn.close()
		self.log('client offline')
		self.online = False

	def start(self):
		pass

	def run(self):
		self.log('client online')
		self.online = True
		while self.online:
			try:
				data = self.AESCryptor.decrypt(self.conn.recv(1024))
			except socket.error:
				self.log('failed to recieve data, stopping client now')
				self.stop(False)
			else:
				if not self.online:
					break
				if data:
					self.processData(data)
				else:
					self.log('received empty data, stopping client now')
					self.stop(False)
			time.sleep(0.2)

	def processData(self, data):
		try:
			js = json.loads(data)
		except:
			self.log('fail to read received json')
			self.log('recieved: ' + data)
			return
		action = js['action']
		if action == 'message':
			self.recieveMessage(js['data'])
		elif action == 'stop':
			self.log('client revieved a stop command')
			self.stop(False)

	def recieveMessage(self, data):
		pass

	def sendMessage(self, msg):
		if self.online:
			js = {'action': 'message', 'data': msg}
			self.conn.sendall(self.AESCryptor.encrypt(json.dumps(js)))

class AESCryptor():
	def __init__(self, key, mode = AES.MODE_CBC):
		self.key = self.__to16Length(key)
		self.mode = mode

	def __to16Length(self, text):
		return text + ('\0' * ((16 - (len(text) % 16)) % 16))

	def encrypt(self, text):
		cryptor = AES.new(self.key, self.mode, self.key)
		return b2a_hex(cryptor.encrypt(self.__to16Length(text)))

	def decrypt(self, text):
		cryptor = AES.new(self.key, self.mode, self.key)
		return cryptor.decrypt(a2b_hex(text)).rstrip('\0')

