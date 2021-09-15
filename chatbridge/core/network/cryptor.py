import hashlib
from binascii import b2a_hex, a2b_hex

from Crypto.Cipher import AES


class AESCryptor:
	def __init__(self, key: str, mode=AES.MODE_CBC):
		self.key: bytes = self.__to_16_length_bytes(key)
		self.__key_empty = len(key) == 0
		self.__hashed_key = hashlib.sha256(self.key).digest()  # a 32-length bytes
		self.mode = mode

	def get_cryptor(self):
		return AES.new(self.__hashed_key, self.mode, self.__hashed_key[:16])

	@staticmethod
	def __to_16_length_bytes(text: str) -> bytes:
		text_bytes = text.encode('utf8')
		return text_bytes + (b'\0' * ((16 - (len(text_bytes) % 16)) % 16))

	def encrypt(self, text: str) -> bytes:
		if self.__key_empty:
			return text.encode('utf8')
		return b2a_hex(self.get_cryptor().encrypt(self.__to_16_length_bytes(text)))

	def decrypt(self, byte_data: bytes) -> str:
		if self.__key_empty:
			return byte_data.decode('utf8')
		return self.get_cryptor().decrypt(a2b_hex(byte_data)).decode('utf8').rstrip('\0')


if __name__ == '__main__':
	aes = AESCryptor('test_pwd')
	while True:
		t = input()
		x = aes.encrypt(t)
		print('Encoded:', x)
		y = aes.decrypt(x)
		print('{} -> {} -> {}'.format(t, x, y))

