from chatbridge.core.client import ChatBridgeClient
from chatbridge.core.config import ClientConfig
from chatbridge.core.network.protocol import ChatPayload
from chatbridge.impl import utils

ConfigFile = 'ChatBridge_client.json'


class CLIClient(ChatBridgeClient):
	def _on_stopped(self):
		super()._on_stopped()
		self.logger.info('Disconnected')

	def on_chat(self, sender: str, payload: ChatPayload):
		self.logger.info('New message: [{}] {}'.format(sender, payload.formatted_str()))

	def console_loop(self):
		while True:
			text = input()
			if len(text) == 0:
				continue

			self.logger.info('Processing user input "{}"'.format(text))
			if text == 'start':
				self.start()
			elif text == 'stop':
				self.stop()
				break
			elif text == 'restart':
				self.restart()
			elif text == 'ping':
				self.logger.info('Ping: {}'.format(self.get_ping_text()))
			elif text == 'help':
				self.logger.info('start: start the client')
				self.logger.info('stop: stop the client and quit')
				self.logger.info('restart: restart the client')
				self.logger.info('ping: display ping')
			else:
				self.broadcast_chat(text)


def main():
	config: ClientConfig = utils.load_config(ConfigFile, ClientConfig)
	client = CLIClient.create(config)
	print('AES Key = {}'.format(config.aes_key))
	print('Client Info: name = {}, password = {}'.format(config.name, config.password))
	print('Server address = {}'.format(client.get_server_address()))
	client.start()
	client.console_loop()


if __name__ == '__main__':
	main()
