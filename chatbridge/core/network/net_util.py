import json
import socket
import struct

from chatbridge.core.network.cryptor import AESCryptor
from chatbridge.core.network.protocol import AbstractPacket

__all__ = [
	'send_data',
	'receive_data',
	'EmptyContent',
]

RECEIVE_BUFFER_SIZE = 1024


class EmptyContent(socket.error):
	pass


def send_data(sock: socket.socket, cryptor: AESCryptor, packet: AbstractPacket):
	encrypted_data = cryptor.encrypt(json.dumps(packet.serialize(), ensure_ascii=False))
	packet_data = struct.pack('I', len(encrypted_data)) + encrypted_data
	sock.sendall(packet_data)


def receive_data(sock: socket.socket, cryptor: AESCryptor, *, timeout: float) -> str:
	sock.settimeout(timeout)
	header = sock.recv(4)
	if len(header) < 4:
		raise EmptyContent('Empty content received')
	remaining_data_length = struct.unpack('I', header)[0]
	encrypted_data = bytes()
	while remaining_data_length > 0:
		buf = sock.recv(min(remaining_data_length, RECEIVE_BUFFER_SIZE))
		encrypted_data += buf
		remaining_data_length -= len(buf)
	return cryptor.decrypt(encrypted_data)
