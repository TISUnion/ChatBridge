import asyncio
from enum import auto, Enum
from queue import Queue, Empty
from typing import NamedTuple, Any, List

import discord
from discord import Message, Webhook, SyncWebhook
from discord.ext import commands
from discord.ext.commands import Context

from chatbridge.common import logger
from chatbridge.core.network.protocol import ChatPayload, PacketType, DiscordChatPayload, CustomPayload
from chatbridge.impl.discord import stored
from chatbridge.impl.discord.config import DiscordConfig
from chatbridge.impl.discord.helps import CommandHelpMessageAll, CommandHelpMessage, StatsCommandHelpMessage
from chatbridge.impl.tis import bot_util


class MessageDataType(Enum):
	CHAT = auto()
	EMBED = auto()
	TEXT = auto()


class MessageData(NamedTuple):
	channel: int
	data: Any
	type: MessageDataType


class DiscordBot(commands.Bot):
	sync_webhook: SyncWebhook

	def __init__(self, command_prefix, **options):
		options['help_command'] = None
		super().__init__(command_prefix, **options)
		self.messages = Queue()
		self.logger = logger.ChatBridgeLogger('Bot', file_handler=stored.client.logger.file_handler)
		try:
			from google_trans_new import google_translator
			self.translator = google_translator()
		except Exception as e:
			self.logger.error('Failed to import google translator: {} {}'.format(type(e), e))
			self.translator = None

	@property
	def config(self) -> DiscordConfig:
		return stored.config

	@property
	async def webhook(self) -> Webhook:
		channel_chat = self.get_channel(self.config.channel_for_chat)
		try:
			webhooks = await channel_chat.webhooks()
			for _webhook in webhooks:
				if _webhook.user == self.user:
					return _webhook
			raise Exception('no valid webhook')
		except:
			return await channel_chat.create_webhook(name='Chatbridge webhook')

	# @property
	# async def 

	def start_running(self):
		self.logger.info('Starting the bot')
		self.run(self.config.bot_token)

	async def listeningMessage(self):
		self.logger.info('Message listening looping...')
		try:
			channel_chat = self.get_channel(self.config.channel_for_chat)
			webhook = await self.webhook
			while True:
				try:
					message_data = self.messages.get(block=False)  # type: MessageData
				except Empty:
					await asyncio.sleep(0.05)
					continue
				data = message_data.data
				discord.Embed()
				if message_data.type == MessageDataType.CHAT:  # chat message
					assert isinstance(data, tuple)
					sender: str = data[0]
					payload: ChatPayload = data[1]
					# if self.translator is not None:
					# 	try:
					# 		translation = self.translator.translate(data.message, lang_tgt='en')
					# 		dest = 'en'
					# 		if translation.src != dest:
					# 			message += '   | [{} -> {}] {}'.format(translation.src, dest, translation.text)
					# 	except:
					# 		self.logger.error('Translate fail')
					if payload.author:
						await webhook.send(payload.message, avatar_url='https://mc-heads.net/avatar/{}'.format(payload.author), username='[{}] {}'.format(sender, payload.author))
					else:
						await channel_chat.send(self.format_message_text('[{}] {}'.format(sender, payload.formatted_str())))

				elif message_data.type == MessageDataType.EMBED:  # embed
					assert isinstance(data, discord.Embed)
					self.logger.debug('Sending embed')
					await self.get_channel(message_data.channel).send(embed=data)
				elif message_data.type == MessageDataType.TEXT:
					await self.get_channel(message_data.channel).send(self.format_message_text(str(data)))
				else:
					self.logger.debug('Unknown messageData type {}'.format(message_data.data))
		except:
			self.logger.exception('Error looping discord bot')
			await self.close()

	async def on_ready(self):
		self.logger.info(f'Logged in as {self.user}')
		webhook = await self.webhook
		self.sync_webhook = SyncWebhook.from_url(webhook.url)
		await self.listeningMessage()

	async def on_message(self, message: Message):
		if message.author == self.user:
			return
		if message.channel.id in self.config.channels_for_command or message.channel.id == self.config.channel_for_chat:
			msg_debug = f'{message.channel}: {message.author}: {message.author.name}: {message.content}'
			args = message.content.split(' ')
			# Command
			if args[0].startswith(self.config.command_prefix) and message.channel.id in self.config.channels_for_command:
				self.logger.info('Command: {}'.format(msg_debug))
				await super().on_message(message)
				if args[0] != '!!qq':
					return
			# Chat
			if message.channel.id == self.config.channel_for_chat:
				webhook = await self.webhook
				# ignore itselves webhook message
				if message.webhook_id == webhook.id:
					return
				self.logger.info('Chat: {}'.format(msg_debug))
				# send direct if the message is player info
				if message.author.id == self.config.server_info_bot_id:
					stored.client.send_to_all(type_=PacketType.custom, payload=CustomPayload(
						data = {
							'type': 'serverinfo',
							'message': message.clean_content.removeprefix('**').removesuffix('**')
						}
					))
					return
				# fetch message info
				color = ''
				author_name = ''
				if message.author.bot:
					color = '#ffffff'
					author_name = message.author.name
				else:
					color = '#' + hex(message.author.color.value).removeprefix('0x')
					# fetch author nickname/name
					author_name = message.author.nick if message.author.nick else message.author.global_name

				# fetch reply message info
				reply_name = ''
				reply_color = ''
				reply_mes = ''
				if message.reference:
					reference: Message = message.reference.resolved
					# fetch reply message info depends on webhook message or not
					if reference.webhook_id:
						# author is a webhook
						author = reference.author
						reply_name = author.display_name
						try:
							reply_name = reply_name.split('] ', 1)[1]
						except:
							reply_name
						reply_color = '#ffffff'
						if reference.embeds:
							embed = reference.embeds[0]
							reply_mes = embed.description
					elif reference.author.bot:
						author = reference.author
						reply_name = author.name
						reply_color = '#ffffff'
					else:
						# author is a member
						channel_chat = self.get_channel(self.config.channel_for_chat)
						author = await channel_chat.guild.fetch_member(reference.author.id)
						reply_name = author.nick if author.nick else author.global_name
						reply_color = '#' + hex(author.color.value).removeprefix('0x')

					if not reply_mes:
						reply_mes = reference.content

				stored.client.braodcast_discord_chat(
					message.author.top_role.name,
					color,
					author_name,
					message.clean_content,
					reply_name,
					reply_color,
					reply_mes
				)

	def add_message(self, data, channel_id, t):
		self.messages.put(MessageData(data=data, channel=channel_id, type=t))

	def add_embed(self, title: str, message_title: str, message: str, channel_id: int):
		embed = discord.Embed(color=discord.Colour.blue())
		embed.set_author(name=title, icon_url=self.config.embed_icon_url)
		embed.add_field(name=message_title, value=message)
		self.add_message(embed, channel_id, MessageDataType.EMBED)

	def add_stats_result(self, stats_name: str, rank_lines: List[str], total: int, channel_id: int):
		msg = ''
		length = 0
		for i, line in enumerate(rank_lines):
			msg += line
			length += len(line)
			if i == len(rank_lines) - 1 or length + len(rank_lines[i + 1]) > 1024:
				embed = discord.Embed(color=discord.Colour.blue())
				embed.set_author(name='Statistic Rank', icon_url=self.config.embed_icon_url)
				rank = [line.split(' ')[0] for line in msg.splitlines()]
				player = [self.format_message_text(line.split(' ')[1]) for line in msg.splitlines()]
				value = [bot_util.process_number(line.split(' ')[2]) for line in msg.splitlines()]
				embed.add_field(name='Stats name', value=stats_name, inline=False)
				embed.add_field(name='Rank', value='\n'.join(rank))
				embed.add_field(name='Player', value='\n'.join(player))
				embed.add_field(name='Value', value='\n'.join(value))
				if i == len(rank_lines) - 1:
					embed.set_footer(text='Total: {} | {}'.format(total, bot_util.process_number(total)))
				self.logger.debug('Adding embed with length {} in message list'.format(len(msg)))
				self.add_message(embed, channel_id, MessageDataType.EMBED)
				msg = ''
				length = 0
			else:
				msg += '\n'
				length += 1

	@staticmethod
	def format_message_text(msg):
		ret = msg
		for c in ['\\', '`', '*', '_', '<', '>', '@']:
			ret = ret.replace(c, '\\' + c)
		return ret


def create_bot() -> DiscordBot:
	config = stored.config

	intents = discord.Intents.default()
	intents.message_content = True
	bot = DiscordBot(config.command_prefix, intents=intents)

	# noinspection PyShadowingBuiltins
	@bot.command()
	async def help(ctx):
		if ctx.message.channel.id == bot.config.channel_for_chat:
			text = CommandHelpMessageAll
		else:
			text = CommandHelpMessage
		await ctx.send(text)

	@bot.command()
	async def ping(ctx: Context):
		await ctx.send('pong!!')

	async def send_chatbridge_command(target_client: str, command: str, ctx: Context):
		if stored.client.is_online():
			bot.logger.info('Sending command "{}" to client {}'.format(command, target_client))
			stored.client.send_command(target_client, command, params={'from_channel': ctx.message.channel.id})
		else:
			await ctx.send('ChatBridge client is offline')

	@bot.command()
	async def online(ctx: Context):
		if ctx.message.channel.id == bot.config.channel_for_chat:  # chat channel only
			await send_chatbridge_command(bot.config.client_to_query_online, '!!online', ctx)

	@bot.command()
	async def stats(ctx: Context, *args):
		args = list(args)
		if len(args) >= 1 and args[0] == 'rank':
			args.pop(0)
		command = '!!stats rank ' + ' '.join(args)
		if len(args) == 0 or len(args) - int(command.find('-bot') != -1) - int(command.find('-all') != -1) != 2:
			await ctx.send(StatsCommandHelpMessage)
		else:
			await send_chatbridge_command(bot.config.client_to_query_stats, command, ctx)

	return bot
