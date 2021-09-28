from chatbridge.core.config import ServerConfig
from chatbridge.core.network.basic import Address
from chatbridge.core.network.protocol import ChatPayload
from chatbridge.core.server import ChatBridgeServer
from chatbridge.impl import utils

ConfigFile = 'ChatBridge_server.json'


class CLIServer(ChatBridgeServer):
	def on_chat(self, sender: str, content: ChatPayload):
		self.logger.info('Chat from {}: {}'.format(sender, content.formatted_str()))

	def console_loop(self):
		while self.is_running():
			text = input()
			self.logger.info('Processing user input "{}"'.format(text))
			if text == 'stop':
				self.stop()
			elif text.startswith('stop') and text.find(' ') != -1:
				target_name = text.split(' ', 1)[1]
				client = self.clients.get(target_name)
				if client is not None:
					self.logger.info('Stopping client {}'.format(target_name))
					client.stop()
				else:
					self.logger.warning('Client {} not found'.format(target_name))
			elif text == 'list':
				self.logger.info('Client count: {}'.format(len(self.clients)))
				for client in self.clients.values():
					self.logger.info('- {}: online = {}, ping = {}'.format(client.info.name, client.is_online(), client.get_ping_text()))
			else:
				print('''
Type "stop" to stop the server
Type "stop client_name" to stop a client
Type "list" to show the client list
'''.strip())


def main():
	config: ServerConfig = utils.load_config(ConfigFile, ServerConfig)
	address = Address(config.hostname, config.port)
	print('AES Key = {}'.format(config.aes_key))
	print('Server address = {}'.format(address.pretty_str()))
	server = CLIServer(config.aes_key, address)
	for i, client_info in enumerate(config.clients):
		print('- Client #{}: name = {}, password = {}'.format(i + 1, client_info.name, client_info.password))
		server.add_client(client_info)
	server.start()
	server.console_loop()


if __name__ == '__main__':
	main()
