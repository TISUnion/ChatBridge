# coding: utf8

from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import json
import socket
import threading
import os
import time

'''
数据包格式：
开始连接：
{
	"action": "start",
	"name": "ClientName",
	"password": "ClientPassword"
}
返回结果：
{
	"action": "result",
	"data": "success"
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

class ChatClientInfo():
	def __init__(self, name, password):
		self.name = name
		self.password = password

	def __eq__(self, other):
		return self.name == other.name and self.password == other.password


class ChatClient():
	def __init__(self, info, cryptorPassword, logFile = None):
		self.online = False
		self.conn = None
		self.thread = None
		self.consoleOutput = True
		self.info = info
		self.logFile = logFile
		self.cryptorPassword = cryptorPassword
		self.AESCryptor = AESCryptor(self.cryptorPassword)

	def __del__(self):
		if self.isOnline():
			self.conn.close()

	def sendData(self, msg):
		self.conn.sendall(self.AESCryptor.encrypt(msg))

	def recieveData(self):
		return self.AESCryptor.decrypt(self.conn.recv(1024))

	def log(self, msg):
		msg = str(msg)
		if type(msg).__name__ == 'unicode':
			msg = msg.encode('utf-8')
		prefix = '[ChatBridgeClient.' + self.info.name + '] '
		msg = prefix.encode('utf-8') + msg
		if self.logFile != None:
			printLog(msg, self.logFile)
		if self.consoleOutput:
			print msg

	def isOnline(self):
		if self.thread != None and self.thread.is_alive() == False:
			self.online = False
		return self.online

	def start(self):
		self.thread = threading.Thread(target = self.run, args = ())
		self.thread.setDaemon(True)
		self.thread.start()

	def stop(self, notifyConnection):
		if not self.isOnline():
			self.log('cannot stop an offline client')
			return
		if notifyConnection:
			self.sendData('{"action": "stop"}')
		self.conn.close()
		self.log('client offline')
		self.online = False

	def run(self):
		self.log('client online')
		self.online = True
		while self.isOnline():
			try:
				data = self.recieveData()
			except socket.error:
				self.log('failed to recieve data, stopping client now')
				self.stop(False)
			else:
				if not self.isOnline():
					break
				if data:
					self.processData(data)
				else:
					self.log('received empty data, stopping client now')
					self.stop(False)

	def __splitJson(self, data):
		ret = []
		depth = 0
		j = 0
		for i in range(len(data)):
			if data[i] == '{':
				depth += 1
			elif data[i] == '}':
				depth -= 1
			if depth == 0:
				ret.append(json.loads(data[j: i + 1]))
				j = i
			if depth < 0:
				raise ValueError
		if depth != 0:
			raise ValueError
		return ret

	def processData(self, data):
		try:
			js = self.__splitJson(data)
		except ValueError:
			self.log('fail to read received json')
			self.log('recieved: ' + data)
			return
		for i in js:
			action = i['action']
			self.log('client revieved action "' + action + '"')
			if action == 'message':
				self.recieveMessage(i['data'])
			elif action == 'result':
				self.processResult(i['data'])
			elif action == 'stop':
				self.stop(False)

	def recieveMessage(self, data):
		pass

	def processResult(self, data):
		pass

	def sendMessage(self, msg):
		if self.isOnline():
			js = {'action': 'message', 'data': msg}
			self.sendData(json.dumps(js))

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

def printLog(msg, logFileName):
	try:
		if type(msg).__name__ == 'unicode':
			msg = msg.encode('utf-8')
		if not os.path.isfile(logFileName):
			with open(logFileName, 'w') as f:
				pass
		with open(logFileName, 'a') as logfile:
			logfile.write(time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time())) + ' ' + msg + '\n')
	except IOError:
		print 'Fail to access log file "', logFileName, '"'
