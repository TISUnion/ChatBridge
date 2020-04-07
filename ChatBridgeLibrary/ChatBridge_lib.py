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
import random

LibVersion = 'v20200116'
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
clientA -> server -> clientB
{
	"action": "command",
	"sender": "CLIENT_A_NAME",
	"receiver": "CLIENT_B_NAME",
	"command": "COMMAND",
	"result": 
	{
		"responded": false
	}
}
clientA <- server <- clientB
{
	"action": "command",
	"sender": "CLIENT_A_NAME",
	"receiver": "CLIENT_B_NAME",
	"command": "COMMAND",
	"result": 
	{
		"responded": true,
		...
	}
}
	[!!stats]
	"result": 
	{
		"responded": xxx,
		"type": int,  // 0: good, 1: stats not found, 2: stats helper not found
		"stats_name": "aaa.bbb", // if good
		"result": "STRING" // if good
	}
	[!!online]
	"result": 
	{
		"responded": xxx,
		"type": int,  // 0: good, 1: rcon query fail, 2: rcon not found
		"result": "STRING" // if good
	}

保持链接
sender -> receiver
{
	"action": "keepAlive",
	"type": "ping"
}
receiver -> sender
{
	"action": "keepAlive",
	"type": "pong"
}
等待KeepAliveTimeWait秒无响应即可中断连接
'''

KeepAliveTimeWait = 30
keepAliveInterval = 60


class ChatClientInfo():
	def __init__(self, name, password):
		self.name = utils.toUTF8(name)
		self.password = utils.toUTF8(password)

	def __eq__(self, other):
		return self.name == other.name and self.password == other.password


class ChatBridgeBase(object):
	sock = None
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

	def recieveData(self, sock=None, timeout=None):
		if sock == None:
			sock = self.sock
		sock.settimeout(timeout)
		header = sock.recv(4)
		if len(header) < 4:
			return ''
		length = struct.unpack('I', header)[0]
		msg = ''
		sock.settimeout(5)
		while length > 0:
			buf = sock.recv(min(length, self.ReceiveBufferSize))
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

	def send_keepAlive(self, type, sock=None):
		js = {
			'action': 'keepAlive',
			'type': type
		}
		self.sendData(json.dumps(js), sock)

	def on_recieve_result(self, data):
		pass

	def on_recieve_login(self, data):
		pass

	def on_recieve_message(self, data):
		pass

	def on_recieve_command(self, data):
		pass

	def on_recieve_stop(self, data):
		pass

	def on_recieve_keepAlive(self, data):
		pass


class ChatClientBase(ChatBridgeBase):
	threadRun = None
	threadKeepAlive = None
	def __init__(self, info, AESKey, logFile=None):
		super(ChatClientBase, self).__init__('Client.' + info.name, logFile, AESKey)
		self.info = info
		self.isStopping = False  # 当调用stop时设为True
		self.keepAliveResponded = False  # 是否得到keepAlive的pong回应

	def isOnline(self):
		if self.threadRun != None and self.threadRun.is_alive() == False:
			self.online = False
		return super(ChatClientBase, self).isOnline()

	def start(self):
		self.threadRun = threading.Thread(target=self.run, args=())
		self.threadRun.setDaemon(True)
		self.threadRun.start()

	def stop(self, notifyConnection=True):
		if self.isStopping:
			return
		self.isStopping = True
		if not self.isOnline():
			self.log('Cannot stop an offline client')
			return
		try:
			if notifyConnection:
				self.send_stop()
		except Exception as err:
			self.log('Fail to send stop message, error = {}'.format(err.args))
		try:
			self.sock.close()
		except Exception as err:
			self.log('Fail to close socket, error = {}'.format(err.args))
		self.log('Client stopped')
		self.online = False

	def sendData(self, msg, sock=None):
		try:
			super(ChatClientBase, self).sendData(msg, sock)
		except socket.error as err:
			self.log('Fail to send data "{}" to server / client, error = {}'.format(utils.lengthLimit(msg), err.args))
			if self.isOnline():
				self.stop(False)

	def keepAlive(self):
		global KeepAliveTimeWait
		keepAliveTimer = time.time() - random.randint(0, int(KeepAliveTimeWait / 2))
		while self.isOnline():
			if time.time() - keepAliveTimer >= keepAliveInterval:
				try:
					self.keepAliveResponded = False
					self.log('Keep alive pinging...')
					self.send_keepAlive('ping')
				except socket.error as err:
					self.log('Failed to send keep alive data, error = {}, stopping client now'.format(err.args))
					self.stop()
				else:
					keepAliveSentTime = time.time()
					while self.isOnline() and self.keepAliveResponded == False and time.time() - keepAliveSentTime <= KeepAliveTimeWait:
						utils.sleep()
					if not self.isOnline():
						break
					if self.keepAliveResponded:
						self.log('Keep alive responded, ping = {}ms'.format(round((time.time() - keepAliveSentTime) * 1000, 1)))
					else:
						self.log('No respond for keep alive, stop the client')
						self.stop()
					keepAliveTimer = time.time()
			utils.sleep()

	def on_recieve_keepAlive(self, data):
		if data['type'] == 'ping':
			self.send_keepAlive('pong')
		elif data['type'] == 'pong':
			self.keepAliveResponded = True

	def run(self):
		try:
			self.log('Client starting')
			self.online = True
			self.isStopping = False
			self.threadKeepAlive = threading.Thread(target=self.keepAlive, args=())
			self.threadKeepAlive.setDaemon(True)
			self.threadKeepAlive.start()
			while self.isOnline():
				try:
					self.log('[Thread run] waiting for data recieved')
					data = self.recieveData()
					if not self.isOnline():
						break
				except socket.timeout:
					self.log('Timeout, ignore')
				except socket.error as err:
					if self.isStopping:
						pass
					else:
						self.log('Failed to receive data, error = {}, stopping client now'.format(err.args))
						self.stop(True)
				else:
					if not self.isOnline():
						break
					if data:
						self.processData(data)
					else:
						self.log('Received empty data, stopping client now')
						self.stop(True)
		except:
			print('Error running client ' + self.info.name)
			print(traceback.format_exc())
			self.stop(True)
		self.threadRun = None

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
		elif action == 'keepAlive':
			self.on_recieve_keepAlive(js)

	def send_message(self, client, player, message, sock=None):
		if self.isOnline():
			super(ChatClientBase, self).send_message(client, player, message, sock)
		else:
			self.log('Cannot send message since client is offline')

	def send_command_query(self, receiver, command, sock=None):
		js = {
			'action': 'command',
			'sender': self.info.name,
			'receiver': receiver,
			'command': command,
			'result': {
				'responded': False
			}
		}
		self.sendData(json.dumps(js), sock)

	def send_command(self, sender, receiver, command, result, sock=None):
		if self.isOnline():
			super(ChatClientBase, self).send_command(sender, receiver, command, result, sock)
		else:
			self.log('Cannot send command since client is offline')

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
