import os
from threading import Lock
from typing import Optional

from mcdreforged.api.all import *

from chatbridge.common import logger
from chatbridge.impl.mcdr.client import ChatBridgeMCDRClient
from chatbridge.impl.mcdr.config import MCDRClientConfig

Prefixes = ('!!ChatBridge', '!!cb')
client: Optional[ChatBridgeMCDRClient] = None
config: Optional[MCDRClientConfig] = None
server_inst: PluginServerInterface
create_lock = Lock()


@new_thread('ChatBridge-create')
def create_client():
	if create_lock.acquire(blocking=False):
		try:
			if config is not None:
				global client
				server_inst.logger.info('Creating ChatBridgeMCDRClient')
				client = ChatBridgeMCDRClient(config, server_inst)
				client.start()
		finally:
			create_lock.release()


def display_help(source: CommandSource):
	HelpMessage = '''------MCDR ChatBridge插件 v2.0------
一个跨服聊天客户端插件
§a【格式说明】§r
§7{0}§r 显示帮助信息
§7{0} status§r 查看跨服聊天状态
§7{0} restart§r 重启跨服聊天
'''.format(Prefixes[0])
	source.reply(HelpMessage)


def display_status(source: CommandSource):
	if config is None:
		source.reply('跨服聊天未初始化，请检查服务端后台输出')
	else:
		source.reply('跨服聊天客户端在线情况: {}'.format(client is not None and client.is_online()))


def restart_client(source: CommandSource):
	global client
	if config is None:
		source.reply('跨服聊天未初始化，请检查服务端后台输出')
	else:
		if client is not None:
			client.stop()
		create_client()


def on_load(server: PluginServerInterface, old):
	global client, config, server_inst
	if not os.path.isfile(os.path.join('config', server.get_self_metadata().id, 'config.json')):
		server.logger.exception('Config file not found! ChatBridge will not work properly')
		server.logger.error('Fill the default configure file with correct values and reload the plugin')
		server.save_config_simple(MCDRClientConfig.get_default())
		return

	try:
		config = server.load_config_simple(target_class=MCDRClientConfig)
	except:
		server.logger.exception('Failed to read the config file! ChatBridge will not work properly')
		server.logger.error('Fix the configure file and then reload the plugin')
		return
	if config.debug:
		logger.DEBUG_SWITCH = True
	server_inst = server
	for prefix in Prefixes:
		server.register_help_message(prefix, '跨服聊天控制')
	server.register_command(
		Literal(Prefixes).
		runs(display_help).
		then(Literal('status').runs(display_status)).
		then(Literal('restart').runs(restart_client))
	)
	create_client()


@new_thread('ChatBridge-messenger')
def send_chat(message: str, *, author: str = ''):
	if client is None:
		create_client().join()
	client.send_chat(author, message)


def on_user_info(server: PluginServerInterface, info: Info):
	if info.is_from_server:
		send_chat(info.content, author=info.player)


def on_player_joined(server: PluginServerInterface, player_name: str, info: Info):
	send_chat('{} joined {}'.format(player_name, config.name))


def on_player_left(server: PluginServerInterface, player_name: str):
	send_chat('{} left {}'.format(player_name, config.name))


def on_server_startup(server: PluginServerInterface):
	send_chat('Server has started up')


def on_server_stop(server: PluginServerInterface, return_code: int):
	send_chat('Server stopped')


@new_thread('ChatBridge-stop')
def on_unload(server: PluginServerInterface):
	if client is not None:
		client.stop()
