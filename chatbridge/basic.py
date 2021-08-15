import json
import socket
import struct
from typing import Optional

from chatbridge.cryptor import AESCryptor


class ChatBridgeBase(object):
	sock: socket.socket
	RECEIVE_BUFFER_SIZE = 1024

	def __init__(self, aes_key: str):
		self.cryptor = AESCryptor(aes_key)

	def __del__(self):
		if self.isOnline() and self.sock != None:
			self.sock.close()

	def _send_data(self, text: str):
		encrypted_data = self.cryptor.encrypt(text)
		packet_data = struct.pack('I', len(encrypted_data)) + encrypted_data
		self.sock.sendall(packet_data)

	def _receive_data(self, timeout: Optional[float] = None) -> str:
		self.sock.settimeout(timeout)
		header = self.sock.recv(4)
		if len(header) < 4:
			return ''
		self.sock.settimeout(5)
		remaining_data_length = struct.unpack('I', header)[0]
		encrypted_data = bytes()
		while remaining_data_length > 0:
			buf = self.sock.recv(min(remaining_data_length, self.RECEIVE_BUFFER_SIZE))
			encrypted_data += buf
			remaining_data_length -= len(buf)
		return self.cryptor.decrypt(encrypted_data)
