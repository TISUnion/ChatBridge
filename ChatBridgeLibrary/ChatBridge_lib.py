# coding: utf8

from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import json
import socket
import threading
import os
import time
import sys
import traceback

LibVersion = 'v20191107'
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


class ChatBridgeBase(object):
	sock = None
	thread = None
	online = False
	consoleOutput = True
	ReceiveBufferSize = 1024

	def __init__(self, logName, logFile, AESKey):
		self.logName = logName
		self.logFile = logFile
		self.AESKey = AESKey
		self.AESCryptor = AESCryptor(self.AESKey)

	def __del__(self):
		if self.isOnline() and self.sock != None:
			self.sock.close()

	def sendData(self, msg, sock = None):
		if sock == None:
			sock = self.sock
		msg = self.AESCryptor.encrypt(msg)
		if sys.version_info.major == 2:
			sock.sendall(msg)
		else:
			sock.sendall(bytes(msg, encoding = 'utf-8'))

	def recieveData(self, sock = None):
		if sock == None:
			sock = self.sock
		msg = sock.recv(self.ReceiveBufferSize)
		if sys.version_info.major == 2:
			msg = msg
		else:
			msg = str(msg, encoding = 'utf-8')
		return self.AESCryptor.decrypt(msg)

	def log(self, msg):
		msg = stringAdd('[' + self.logName + '] ', msg)
		if self.logFile != None:
			printLog(msg, self.logFile)
		if self.consoleOutput:
			print(msg)

	def isOnline(self):
		if self.thread != None and self.thread.is_alive() == False:
			self.online = False
		return self.online


class ChatClientBase(ChatBridgeBase):
	def __init__(self, info, AESKey, logFile = None):
		super(ChatClientBase, self).__init__('Client.' + info.name, logFile, AESKey)
		self.info = info

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
		self.sock.close()
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
					self.log('Failed to receive data, stopping client now')
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
			self.stop(True)
			print('Error running client ' + self.info.name)
			print(traceback.format_exc())

	def processData(self, data):
		try:
			js = json.loads(data)
		except ValueError:
			self.log('Fail to read received json')
			self.log(stringAdd('Received: ', data))
			return
		action = js['action']
		self.log('Client received action "' + action + '"')
		if action == 'message':
			self.recieveMessage(js['data'])
		elif action == 'result':
			self.recieveResult(js['data'])
		elif action == 'stop':
			self.stop(False)

	def recieveMessage(self, data):
		pass

	def recieveResult(self, data):
		pass

	def sendMessage(self, msg):
		if self.isOnline():
			js = {'action': 'message', 'data': msg}
			self.sendData(json.dumps(js))
			return True
		else:
			return False

class AESCryptor():
	# key and text needs to be utf-8 str in python2 or str in python3
	def __init__(self, key, mode = AES.MODE_CBC):
		self.key = self.__to16Length(key)
		self.mode = mode

	def __to16Length(self, text):
		if sys.version_info.major == 3:
			text = bytes(text, encoding = 'utf-8')
		return text + (b'\0' * ((16 - (len(text) % 16)) % 16))

	def encrypt(self, text):
		cryptor = AES.new(self.key, self.mode, self.key)
		text = self.__to16Length(text)
		result = b2a_hex(cryptor.encrypt(text))
		if sys.version_info.major == 3:
			result = str(result, encoding = 'utf-8')
		return result

	def decrypt(self, text):
		cryptor = AES.new(self.key, self.mode, self.key)
		if sys.version_info.major == 3:
			text = bytes(text, encoding = 'utf-8')
		result = cryptor.decrypt(a2b_hex(text))
		if sys.version_info.major == 3:
			try:
				result = str(result, encoding = 'utf-8')
			except UnicodeDecodeError:
				print('err at decrypt string conversion')
				print('raw result = ', result)
				result = str(result, encoding = 'ISO-8859-1')
				print('ISO-8859-1 = ', result)
		return result.rstrip('\0')

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

# for python2 stuffs
def toUTF8(str):
	if sys.version_info.major == 3:
		return str
	return str.encode('utf-8') if type(str).__name__ == 'unicode' else str

def stringAdd(a, b):
	return toUTF8(a) + toUTF8(b)

def addressToString(addr):
	return '{0}:{1}'.format(addr[0], addr[1])
