from typing import Optional

from mcdreforged.api.all import *

from chatbridge.core.client import ChatBridgeClient
from chatbridge.core.network.protocol import ChatPayload, CommandPayload, DiscordChatPayload, CustomPayload
from chatbridge.impl.mcdr.config import MCDRClientConfig
from chatbridge.impl.tis.protocol import StatsQueryResult, OnlineQueryResult


class ChatBridgeMCDRClient(ChatBridgeClient):
	KEEP_ALIVE_THREAD_NAME = 'ChatBridge-KeepAlive'

	def __init__(self, config: MCDRClientConfig, server: ServerInterface):
		super().__init__(config.aes_key, config.client_info, server_address=config.server_address)
		self.config = config
		self.server: ServerInterface = server
		prev_handler = self.logger.console_handler
		new_handler = SyncStdoutStreamHandler()  # use MCDR's, so the concurrent output won't be messed up
		new_handler.setFormatter(prev_handler.formatter)
		self.logger.removeHandler(prev_handler)
		self.logger.addHandler(new_handler)

	def get_logging_name(self) -> str:
		return 'ChatBridge@{}'.format(hex((id(self) >> 16) & (id(self) & 0xFFFF))[2:].rjust(4, '0'))

	def _get_main_loop_thread_name(self):
		return 'ChatBridge-' + super()._get_main_loop_thread_name()

	def _get_keep_alive_thread_name(self):
		return 'ChatBridge-' + super()._get_keep_alive_thread_name()

	def _on_stopped(self):
		super()._on_stopped()
		self.logger.info('Client stopped')

	def on_chat(self, sender: str, payload: ChatPayload):
		if not self.config.send_to_minecraft.chat: return
		self.server.say(RText('[{}] {}'.format(sender, payload.formatted_str()), RColor.gray))

	def on_discord_chat(self, sender: str, payload: DiscordChatPayload):
		if not self.config.send_to_minecraft.discord_chat: return
		self.server.say(payload.rtext_list)

	def on_command(self, sender: str, payload: CommandPayload):
		is_ask = not payload.responded
		command = payload.command
		result: Optional[Serializable] = None
		if command.startswith('!!stats '):  # !!stats request
			try:
				import stats_helper
			except (ImportError, ModuleNotFoundError):
				result = StatsQueryResult.no_plugin()
			else:
				trimmed_command = command.replace('-bot', '').replace('-all', '')
				res_raw: Optional[str]
				try:
					prefix, typ, cls, target = trimmed_command.split()
					assert typ == 'rank' and type(target) is str
				except:
					res_raw = None
				else:
					res_raw = stats_helper.show_rank(
						self.server.get_plugin_command_source(),
						cls, target,
						list_bot='-bot' in command,
						is_tell=False,
						is_all='-all' in command,
						is_called=True
					)
				if res_raw is not None:
					lines = res_raw.splitlines()
					stats_name = lines[0]
					total = int(lines[-1].split(' ')[1])
					result = StatsQueryResult.create(stats_name, lines[1:-1], total)
				else:
					result = StatsQueryResult.unknown_stat()
		elif command == '!!online':  # !!online response
			player = payload.params.get('player')
			if player is None:
				self.logger.warning('No player in params, params {}'.format(payload.params))
			else:
				result: OnlineQueryResult = OnlineQueryResult.deserialize(payload.result)
				for line in result.data:
					self.server.tell(player, line)

		if is_ask and result is not None:
			self.reply_command(sender, payload, result)

	def query_online(self, client_to_query_online: str, player: str):
		self.send_command(client_to_query_online, '!!online', params={'player': player})

	@new_thread
	def on_custom(self, sender: str, payload: CustomPayload):
		self.server.logger.info(payload)
		conf = self.config.send_to_minecraft
		if payload.data['type'] == 'serverinfo':
			if not conf.server_info: return
			self.server.say(RText('[{}] {}'.format('Spoon', payload.data['message']), RColor.gray))
		elif payload.data['type'] == 'player-join-leave':
			if not conf.player_join_leave: return
			server = payload.data['server']
			if server == self.get_name(): return
			is_join = payload.data['join']
			player = payload.data['player']
			msg = '加入了遊戲' if is_join else '離開了遊戲'
			self.server.say(RText(f'[{server}] {player} {msg}', RColor.gray))
		elif payload.data['type'] == 'player-swap-server':
			if not conf.player_swap_server: return
			_from = payload.data['from']
			_to = payload.data['to']
			player = payload.data['player']
			self.server.say(RText(f'[{_from}] {player} 移動到 {_to}', RColor.gray))
		elif payload.data['type'] == 'server-start-stop':
			if not conf.server_start_stop: return
			server = sender
			msg = '已啟動' if payload.data['start'] else '已關閉'
			self.server.say(RText(f'[{server}] 伺服器{msg}', RColor.gray))
		elif payload.data['type'] == 'player-first-join':
			self.server.logger.info('fsas')
			if not conf.player_first_join: return
			player = payload.data['player']
			self.server.say(RText(f'有一隻新湯匙🥄 {player} 掉在新手村', RColor.gold))

