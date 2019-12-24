# coding: utf8

from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import json
import socket
import threading
import ChatBridgeLibrary.ChatBridge_utils as utils
import time
import sys
import struct
import traceback

LibVersion = 'v20191224'
'''
数据包格式：
4 byte长的unsigned int代表长度，随后是所指长度的加密字符串，解密后为一个json
json格式：
返回结果： server -> client
{
	"action": "result",
	"result": "RESULT"
}
开始连接： client -> server
{
	"action": "login",
	"name": "ClientName",
	"password": "ClientPassword"
}
返回登录情况：server -> client 返回结果
	"result": login success" // 成功
	"result": login fail" // 失败
		
传输信息： client <-> server
{
	"action": "message",
	"client": "CLIENT_NAME",
	"player": "PLAYER_NAME",
	"message": "MESSAGE_STRING"
}
结束连接： client <-> server
{
	"action": "stop"
}

调用指令：
A -> server -> B
clientA -> server
{
	"action": "command",
	"sender": "CLIENT_A_NAME",
	"receiver": "CLIENT_B_NAME",
	"command": "COMMAND",
	"result": "RESULT"
}
'''

CommandNoneResult = '_@#NoneResult#@_'


class ChatClientInfo():
	def __init__(self, name, password):
		self.name = utils.toUTF8(name)
		self.password = utils.toUTF8(password)

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

	def sendData(self, msg, sock=None):
		if sock == None:
			sock = self.sock
		msg = self.AESCryptor.encrypt(msg)
		if sys.version_info.major == 3:
			msg = bytes(msg, encoding='utf-8')
		sock.sendall(struct.pack('I', len(msg)))
		sock.sendall(msg)

	def recieveData(self, sock=None):
		if sock == None:
			sock = self.sock
		sock.settimeout(None)
		header = sock.recv(4)
		if len(header) < 4:
			return ''
		length = struct.unpack('I', header)[0]
		msg = ''
		sock.settimeout(5)
		while length > 0:
			buf = sock.recv(self.ReceiveBufferSize)
			if sys.version_info.major == 3:
				buf = str(buf, encoding='utf-8')
			msg += buf
			length -= len(buf)
		return self.AESCryptor.decrypt(msg)

	def log(self, msg, fileName = None):
		if fileName == None:
			fileName = self.logFile
		msg = utils.stringAdd('[' + self.logName + '] ', msg)
		t = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time())) + ' '
		msg = utils.stringAdd(t, msg)
		if fileName != None:
			utils.printLog(msg, fileName)
		if self.consoleOutput:
			print(msg)

	def isOnline(self):
		if self.thread != None and self.thread.is_alive() == False:
			self.online = False
		return self.online

	def send_result(self, result, sock=None):
		js = {
			'action': 'result',
			'result': result
		}
		self.sendData(json.dumps(js), sock)

	def send_login(self, name, password, sock=None):
		js = {
			'action': 'login',
			'name': name,
			'password': password
		}
		self.sendData(json.dumps(js), sock)

	def send_message(self, client, player, message, sock=None):
		js = {
			'action': 'message',
			'client': client,
			'player': player,
			'message': message
		}
		self.sendData(json.dumps(js), sock)

	def send_command(self, sender, receiver, command, result, sock=None):
		js = {
			'action': 'command',
			'sender': sender,
			'receiver': receiver,
			'command': command,
			'result': result
		}
		self.sendData(json.dumps(js), sock)

	def send_stop(self, sock=None):
		js = {
			'action': 'stop'
		}
		self.sendData(json.dumps(js), sock)


class ChatClientBase(ChatBridgeBase):
	def __init__(self, info, AESKey, logFile=None):
		super(ChatClientBase, self).__init__('Client.' + info.name, logFile, AESKey)
		self.info = info

	def start(self):
		self.thread = threading.Thread(target=self.run, args=())
		self.thread.setDaemon(True)
		self.thread.start()

	def stop(self, notifyConnection):
		if not self.isOnline():
			self.log('Cannot stop an offline client')
			return
		if notifyConnection:
			self.send_stop()
		self.sock.close()
		self.log('Client stopped')
		self.online = False

	def sendData(self, msg, sock=None):
		try:
			super(ChatClientBase, self).sendData(msg, sock)
		except socket.error:
			self.log('Fail to send data to server')
			if self.isOnline():
				self.stop(False)

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
			print('Error running client ' + self.info.name)
			print(traceback.format_exc())
			self.stop(True)

	def processData(self, data):
		try:
			js = json.loads(data)
		except ValueError:
			self.log('Fail to read received json')
			self.log(utils.stringAdd('Received: ', data))
			return
		action = js['action']
		self.log('Client received action "' + action + '"')
		if action == 'result':
			self.on_recieve_result(js)
		elif action == 'login':
			self.on_recieve_login(js)
		elif action == 'message':
			self.on_recieve_message(js)
		elif action == 'command':
			self.on_recieve_command(js)
		elif action == 'stop':
			self.on_recieve_stop(js)

	def send_message(self, client, player, message, sock=None):
		if self.isOnline():
			super(ChatClientBase, self).send_message(client, player, message, sock)
		else:
			self.log('Cannot send message since client is offline')

	def send_command(self, receiver, command, result=CommandNoneResult, sock=None):
		if self.isOnline():
			super(ChatClientBase, self).send_command(self.info.name, receiver, command, result, sock)
		else:
			self.log('Cannot send command since client is offline')

	def on_recieve_result(self, data):
		pass

	def on_recieve_login(self, data):
		pass

	def on_recieve_message(self, data):
		pass

	def on_recieve_command(self, data):
		pass

	def on_recieve_stop(self, data):
		self.stop(False)


class AESCryptor():
	# key and text needs to be utf-8 str in python2 or str in python3
	def __init__(self, key, mode=AES.MODE_CBC):
		self.key = self.__to16Length(key)
		self.mode = mode

	def __to16Length(self, text):
		if sys.version_info.major == 3:
			text = bytes(text, encoding='utf-8')
		return text + (b'\0' * ((16 - (len(text) % 16)) % 16))

	def encrypt(self, text):
		cryptor = AES.new(self.key, self.mode, self.key)
		text = self.__to16Length(text)
		result = b2a_hex(cryptor.encrypt(text))
		if sys.version_info.major == 3:
			result = str(result, encoding='utf-8')
		return result

	def decrypt(self, text):
		cryptor = AES.new(self.key, self.mode, self.key)
		if sys.version_info.major == 3:
			text = bytes(text, encoding='utf-8')
		try:
			result = cryptor.decrypt(a2b_hex(text))
		except TypeError as err:
			print('TypeError when decrypting text')
			print('text =', text)
			raise err
		except ValueError as err:
			print(err.args)
			print('len(text) =', len(text))
			raise err
		if sys.version_info.major == 3:
			try:
				result = str(result, encoding='utf-8')
			except UnicodeDecodeError:
				print('error at decrypt string conversion')
				print('raw result = ', result)
				result = str(result, encoding='ISO-8859-1')
				print('ISO-8859-1 = ', result)
		return result.rstrip('\0')
