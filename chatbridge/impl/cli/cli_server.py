import sys
import threading
import time
import traceback

from chatbridge.core.config import ServerConfig
from chatbridge.core.network.basic import Address
from chatbridge.core.network.protocol import ChatPayload
from chatbridge.core.server import ChatBridgeServer
from chatbridge.impl import utils


class CLIServerConfig(ServerConfig):
	show_chat: bool = True
	log_chat: bool = False


config: CLIServerConfig
ConfigFile = 'ChatBridge_server.json'
CHAT_LOGGING_FILE = 'chat.log'


def thread_dump() -> str:
	from sys import _current_frames
	lines = []
	name_map = dict([(thread.ident, thread.name) for thread in threading.enumerate()])
	for thread_id, stack in _current_frames().items():
		lines.append("# Thread {} ({})".format(name_map.get(thread_id, 'unknown'), thread_id))
		for filename, lineno, name, line in traceback.extract_stack(stack):
			lines.append('  File "{}", line {}, in {}'.format(filename, lineno, name))
			if line:
				lines.append('    {}'.format(line.strip()))
	return '\n'.join(lines)


class CLIServer(ChatBridgeServer):
	def on_chat(self, sender: str, content: ChatPayload):
		if config.show_chat:
			self.logger.info('Chat from {}: {}'.format(sender, content.formatted_str()))
		if config.log_chat:
			try:
				with open(CHAT_LOGGING_FILE, 'a') as file:
					file.write('[{}] [{}] {}\n'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), sender, content.formatted_str()))
			except Exception as e:
				self.logger.error('Failed to log chat message: {} {}'.format(type(e), e))

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
			elif text == 'debug on':
				self.logger.set_debug_all(True)
				self.logger.info('Debug logging on')
			elif text == 'debug off':
				self.logger.set_debug_all(False)
				self.logger.info('Debug logging off')
			elif text == 'thread_dump':
				self.logger.info(thread_dump())
			else:
				self.logger.info('stop": stop the server')
				self.logger.info('stop <client_name>": stop a client')
				self.logger.info('list": show the client list')
				self.logger.info('debug on|off": switch debug logging')


def main():
	global config
	config = utils.load_config(ConfigFile, CLIServerConfig)
	address = Address(config.hostname, config.port)
	print('AES Key = {}'.format(config.aes_key))
	print('Server address = {}'.format(address))
	server = CLIServer(config.aes_key, address)
	for i, client_info in enumerate(config.clients):
		print('- Client #{}: name = {}, password = {}'.format(i + 1, client_info.name, client_info.password))
		server.add_client(client_info)
	server.start()

	if sys.stdin.isatty():
		server.console_loop()
	else:
		utils.wait_until_terminate()
		server.stop()


if __name__ == '__main__':
	main()
