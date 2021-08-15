import json
from enum import Enum, auto


class PayloadType:
	login = "login"
	logout = "logout"
	request = "request"
	response = "response"
	chat = "chat"


class Packet:
	def __init__(self, payload_type: str, payload: dict):
		self.payload_type = payload_type
		self.payload = payload

	def to_str(self):
		return json.dumps({
			'type': self.payload_type,
			'payload': self.payload
		}, ensure_ascii=False)

	@staticmethod
	def from_str(json_str: str):
		json_obj = json.loads(json_str)
		return Packet(json_obj['type'], json_obj['payload'])


w = Packet(PayloadType.login, {'asd': 'asd'}).to_str()
print(w)
print(Packet.from_str(w).to_str())
