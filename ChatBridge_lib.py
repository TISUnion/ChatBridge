# coding: utf8

from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import json
import socket
import threading
import os
import time
import traceback

'''
数据包格式：
开始连接： client -> server
{
	"action": "start",
	"name": "ClientName",
	"password": "ClientPassword"
}
返回结果： server -> client
{
	"action": "result",
	"data": "success"
}
传输信息： client <-> server
{
	"action": "message",
	"data": "MESSAGE_STRING"
}
结束连接： client <-> server
{
	"action": "stop"
}
'''

class ChatClientInfo():
	def __init__(self, name, password):
		self.name = toUTF8(name)
		self.password = toUTF8(password)

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
		msg = stringAdd('[ChatBridgeClient.' + self.info.name + '] ', msg)
		if self.logFile != None:
			printLog(msg, self.logFile)
		if self.consoleOutput:
			print(msg)

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
			self.log('Cannot stop an offline client')
			return
		if notifyConnection:
			self.sendData('{"action": "stop"}')
		self.conn.close()
		self.log('Client stopped')
		self.online = False

	def run(self):
		try:
			self.log('Client starting')
			self.online = True
			while self.isOnline():
				try:
					data = self.recieveData()
				except socket.error:
					self.log('Failed to recieve data, stopping client now')
					self.stop(False)
				else:
					if not self.isOnline():
						break
					if data:
						self.processData(data)
					else:
						self.log('Received empty data, stopping client now')
						self.stop(False)
		except:
			self.stop()
			print('Error running client '+ self.info.name)
			print(traceback.format_exc())

	def processData(self, data):
		try:
			js = json.loads(data)
		except ValueError:
			self.log('Fail to read received json')
			self.log(stringAdd('Recieved: ', data))
			return
		action = js['action']
		self.log('Client revieved action "' + action + '"')
		if action == 'message':
			self.recieveMessage(js['data'])
		elif action == 'result':
			self.processResult(js['data'])
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
		msg = toUTF8(msg)
		if not os.path.isfile(logFileName):
			with open(logFileName, 'w') as f:
				pass
		with open(logFileName, 'a') as logfile:
			logfile.write(time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time())) + ' ' + msg + '\n')
	except IOError:
		print('Fail to access log file "', logFileName, '"')

def toUTF8(str):
	return str.encode('utf-8') if type(str).__name__ == 'unicode' else str

def stringAdd(a, b):
	return toUTF8(a) + toUTF8(b)

def addressToString(addr):
	return '{0}:{1}'.format(addr[0], addr[1])
