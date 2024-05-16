import sys
import threading
import time
import traceback
from typing import Dict

from mcdreforged.api.decorator import new_thread

from chatbridge.core.config import ServerConfig
from chatbridge.core.network.basic import Address
from chatbridge.core.network.protocol import ChatPayload, ChatBridgePacket, PacketType, CustomPayload
from chatbridge.core.server import ChatBridgeServer
from chatbridge.impl import utils


class CLIServerConfig(ServerConfig):
	show_chat: bool = True
	log_chat: bool = False


config: CLIServerConfig
ConfigFile = 'ChatBridge_server.json'
CHAT_LOGGING_FILE = 'chat.log'


class PlayerSwapServerInfo():
	join_ts: float = 0
	leave_ts: float = 0
	_from: str = ''
	_to: str = ''

player_swap_dict: Dict[str, PlayerSwapServerInfo] = {}
PLAYER_SWAP_TIMEOUT = 0.2


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


	def broadcast(self, payload: CustomPayload):
		receivers = self.clients.keys()
		for receiver_name in set(receivers):
			client = self.clients.get(receiver_name)
			if client is not None:
				if client.is_online():
					packet = ChatBridgePacket(
						sender=self.get_name(),
						receivers=list(receivers),
						broadcast=True,
						type=PacketType.custom,
						payload=payload.serialize()
					)
					client.send_packet_invoker(packet)


	@new_thread('chatbridge-server-player-swap')
	def on_packet(self, packet: ChatBridgePacket):
		if packet.type == PacketType.custom:
			payload = CustomPayload.deserialize(packet.payload)
			if payload.data['type'] != 'player-join-leave':
				return
			# handle player-join-leave packet
			player = payload.data['player']
			join = payload.data['join']
			server = packet.sender
			swap = player_swap_dict.get(player)

			if swap:
				# if has been waiting
				if join:
					if not swap.join_ts and swap.leave_ts and swap._from != server:
						# has been left
						self.logger.info('join')
						swap.join_ts = time.time()
						swap._to = server
						return
				else:
					if swap.join_ts and not swap.leave_ts and swap._to != server:
						# has been joined
						self.logger.info('leave')
						swap.leave_ts = time.time()
						swap._from = server
						return

				# not a swap, send packet normally
				_from = ''
				_to = ''
				if join:
					_to = server
					_from = swap._from
				else:
					_to = swap._to
					_from = server
					

				self.broadcast(CustomPayload(data={
					'type': 'player-join-leave',
					'player': player,
					'join': True,
					'server': _to
				}))
				self.broadcast(CustomPayload(data={
					'type': 'player-join-leave',
					'player': player,
					'join': False,
					'server': _from
				}))
				player_swap_dict.pop(player)
				return

			player_swap_dict[player] = PlayerSwapServerInfo()
			swap = player_swap_dict.get(player)
			if join:
				swap.join_ts = time.time()
				swap._to = server
			else:
				swap.leave_ts = time.time()
				swap._from = server

			# start waiting
			time.sleep(PLAYER_SWAP_TIMEOUT)

			# post waiting
			swap = player_swap_dict.get(player)
			if not swap: return
			duration: float = swap.join_ts - swap.leave_ts
			duration = abs(duration)
			self.logger.info(duration)

			if duration < PLAYER_SWAP_TIMEOUT:
				# swapped server
				self.broadcast(CustomPayload(data={
					'type': 'player-swap-server',
					'player': player,
					'from': swap._from,
					'to': swap._to
				}))
			else:
				# not a swap
				if swap._to:
					self.broadcast(CustomPayload(data={
						'type': 'player-join-leave',
						'player': player,
						'join': True,
						'server': swap._to
					}))
				if swap._from:
					self.broadcast(CustomPayload(data={
						'type': 'player-join-leave',
						'player': player,
						'join': False,
						'server': swap._from
					}))
			
			player_swap_dict.pop(player)



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
