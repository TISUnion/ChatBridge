import traceback

from chatbridge.core.client import ChatBridgeClient
from chatbridge.core.config import ClientInfo, ClientConfig
from chatbridge.core.network.basic import Address
from chatbridge.core.network.protocol import ChatPayload
from chatbridge.impl import utils

ConfigFile = 'ChatBridge_client.json'


class CLIClient(ChatBridgeClient):
	def _on_started(self):
		super()._on_started()
		self.logger.info('Connected to the server')

	def on_chat(self, sender: str, payload: ChatPayload):
		self.logger.info('New message: [{}] {}'.format(sender, payload.formatted_str()))


def main():
	config: ClientConfig = utils.load_config(ConfigFile, ClientConfig)
	server_address = Address(config.server_hostname, config.server_port)
	print('AES Key = {}'.format(config.aes_key))
	print('Client Info: name = {}, password = {}'.format(config.name, config.password))
	print('Server address = {}'.format(server_address.pretty_str()))
	client = CLIClient(config.aes_key, ClientInfo(name=config.name, password=config.password), server_address=server_address)
	client.start()
	try:
		while client.is_online():
			text = input()
			if text == 'stop' or not client.is_online():
				break
			client.send_chat('', text)
	except:
		traceback.print_exc()
		client.stop()


if __name__ == '__main__':
	main()
