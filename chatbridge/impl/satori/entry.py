import asyncio
from typing import Optional

from satori import WebsocketsInfo, Event, EventType
from satori.client import App, Account, ApiInfo

from chatbridge.common.logger import ChatBridgeLogger
from chatbridge.core.client import ChatBridgeClient
from chatbridge.core.network.protocol import ChatPayload, CommandPayload, CustomPayload
from chatbridge.impl import utils
from chatbridge.impl.cqhttp.entry import CQHelpMessage, StatsHelpMessage
from chatbridge.impl.satori.config import SatoriConfig
from chatbridge.impl.tis.protocol import StatsQueryResult, OnlineQueryResult

ConfigFile = 'ChatBridge_satori.json'

config: SatoriConfig
cb_client: Optional['SatoriChatBridgeClient'] = None
satori_client: Optional['SatoriClient'] = None


class SatoriClient:
	def __init__(self):
		self.app = App(WebsocketsInfo(
			host=config.ws_address,
			port=config.ws_port,
			path=config.ws_path,
			token=config.satori_token,
		))
		self.logger = ChatBridgeLogger('Satori', file_handler=cb_client.logger.file_handler)
		self.register_satori_hooks()

		self.__message_queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
		self.__loop: Optional[asyncio.AbstractEventLoop] = None

	def register_satori_hooks(self):
		self.logger.info('Registering satori hooks')

		@self.app.register_on(EventType.MESSAGE_CREATED)
		async def listen(account: Account, event: Event):
			self.logger.debug('Satori MESSAGE_CREATED account={} event={}'.format(account, event))
			if event.channel is None or event.message is None or event.user is None:
				return
			if event.channel.id != str(config.react_channel_id):
				return
			self.logger.info('Satori chat message event: {}'.format(event))

			msg = event.message.content
			args = msg.split(' ')

			async def send_text(s: str):
				await account.send_message(event.channel.id, s)

			if len(args) == 1 and args[0] == '!!help':
				self.logger.info('!!help command triggered')
				await send_text(CQHelpMessage)

			if len(args) == 1 and args[0] == '!!ping':
				self.logger.info('!!ping command triggered')
				await send_text('pong!!')

			if len(args) >= 2 and args[0] == '!!mc':
				self.logger.info('!!mc command triggered')
				sender = event.user.nick or event.user.name
				cb_client.broadcast_chat(msg.split(' ', 1)[-1], sender)

			if len(args) == 1 and args[0] == '!!online':
				self.logger.info('!!online command triggered')
				if cb_client.is_online():
					command = args[0]
					client = config.client_to_query_online
					self.logger.info('Sending command "{}" to client {}'.format(command, client))
					cb_client.send_command(client, command)
				else:
					await send_text('ChatBridge 客户端离线')

			if len(args) >= 1 and args[0] == '!!stats':
				self.logger.info('!!stats command triggered')
				command = '!!stats rank ' + ' '.join(args[1:])
				if len(args) == 0 or len(args) - int(command.find('-bot') != -1) != 3:
					await send_text(StatsHelpMessage)
					return
				if cb_client.is_online:
					client = config.client_to_query_stats
					self.logger.info('Sending command "{}" to client {}'.format(command, client))
					cb_client.send_command(client, command)
				else:
					await send_text('ChatBridge 客户端离线')

	async def __send_text_one(self, text: str):
		account = Account('', 'chatbridge', ApiInfo(
			host=config.ws_address,
			port=config.ws_port,
			path=config.ws_path,
			token=config.satori_token,
		))
		await account.send_message(str(config.react_channel_id), text)

	async def __send_text_long(self, text: str):
		msg = ''
		length = 0
		lines = text.rstrip().splitlines(keepends=True)
		for i in range(len(lines)):
			msg += lines[i]
			length += len(lines[i])
			if i == len(lines) - 1 or length + len(lines[i + 1]) > 500:
				await self.__send_text_one(msg)
				msg = ''
				length = 0

	async def __messanger_loop(self):
		while True:
			msg = await self.__message_queue.get()
			if msg is None:
				break
			try:
				await self.__send_text_long(msg)
			except Exception:
				self.logger.exception('messanger loop error')

	async def main(self):
		self.__loop = asyncio.get_event_loop()
		t = asyncio.create_task(self.__messanger_loop())
		await self.app.run_async()
		await t

	def submit_text(self, s: str):
		if self.__loop is None:
			self.logger.warning('submit_message is called when event loop does not exists yet')
			return

		asyncio.run_coroutine_threadsafe(self.__message_queue.put(s), self.__loop)

	def shutdown(self):
		if self.__loop is not None:
			asyncio.run_coroutine_threadsafe(self.__message_queue.put(None), self.__loop)


class SatoriChatBridgeClient(ChatBridgeClient):
	def on_chat(self, sender: str, payload: ChatPayload):
		if satori_client is None:
			return

		parts = payload.message.split(' ', 1)
		if len(parts) != 2 or (len(config.chatbridge_message_prefix) > 0 and parts[0] != config.chatbridge_message_prefix):
			return

		payload.message = parts[1]
		self.logger.info('Triggered command, sending message {} to satori'.format(payload.formatted_str()))
		satori_client.submit_text('[{}] {}'.format(sender, payload.formatted_str()))

	def on_command(self, sender: str, payload: CommandPayload):
		if satori_client is None:
			return
		if not payload.responded:
			return
		if payload.command.startswith('!!stats '):
			result = StatsQueryResult.deserialize(payload.result)
			if result.success:
				messages = ['====== {} ======'.format(result.stats_name)]
				messages.extend(result.data)
				messages.append('总数：{}'.format(result.total))
				satori_client.submit_text('\n'.join(messages))
			elif result.error_code == 1:
				satori_client.submit_text('统计信息未找到')
			elif result.error_code == 2:
				satori_client.submit_text('StatsHelper 插件未加载')
		elif payload.command == '!!online':
			result = OnlineQueryResult.deserialize(payload.result)
			satori_client.submit_text('====== 玩家列表 ======\n{}'.format('\n'.join(result.data)))

	def on_custom(self, sender: str, payload: CustomPayload):
		if satori_client is None:
			return
		if payload.data.get('cqhttp_client.action') == 'send_text':
			text = payload.data.get('text')
			self.logger.info('Triggered custom text, sending message {} to satori'.format(text))
			satori_client.submit_text(text)


queue = asyncio.Queue()


def main():
	global config, cb_client, satori_client
	config = utils.load_config(ConfigFile, SatoriConfig)

	cb_client = SatoriChatBridgeClient.create(config)
	satori_client = SatoriClient()

	def exit_callback():
		satori_client.shutdown()
		cb_client.stop()

	utils.start_guardian(cb_client)
	utils.register_exit_on_termination(exit_callback)

	print('Starting Satori Bot')
	# cannot use asyncio.run() to create a new one
	# or some "got Future <Future pending> attached to a different loop" error will raise
	asyncio.get_event_loop().run_until_complete(satori_client.main())
	print('Bye~')


if __name__ == '__main__':
	main()
