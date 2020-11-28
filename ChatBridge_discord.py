# -*- coding: UTF-8 -*-
import collections
import os
import json
import queue
import time
import asyncio
import threading
from queue import Queue
from typing import List

import ChatBridge_client
import traceback
import discord
from ChatBridgeLibrary import ChatBridge_lib as lib
from ChatBridgeLibrary import ChatBridge_utils as utils
from googletrans import Translator
from discord.ext import commands

DiscordConfigFile = 'ChatBridge_discord.json'
ClientConfigFile = 'ChatBridge_client.json'
LogFile = 'ChatBridge_discord.log'
RetryTime = 3 # second
EmbedIcon = 'https://cdn.discordapp.com/emojis/566212479487836160.png'
translator = Translator()


class DiscordConfig():
	def __init__(self, configFile):
		js = json.load(open(configFile, 'r'))
		self.token = js['bot_token']
		self.channels_command = js['channels_command']
		self.channel_chat = js['channel_chat']
		self.commandPrefix = js['command_prefix']
		self.clientToQueryStats = js['client_to_query_stats']
		self.clientToQueryOnline = js['client_to_query_online']
		DiscordBot.log('Bot Token = ' + self.token)
		DiscordBot.log('Channel for Commands = ' + str(self.channels_command))
		DiscordBot.log('Channel for Chat = ' + str(self.channel_chat))
		DiscordBot.log('Command Prefix = ' + self.commandPrefix)
		DiscordBot.log('Client to Query !!stats = ' + self.clientToQueryStats)
		DiscordBot.log('Client to Query !!online = ' + self.clientToQueryOnline)


class MessageDataType:
	CHAT = 0
	EMBED = 1
	TEXT = 2


MessageData = collections.namedtuple('MessageData', 'channel data type')


class DiscordBot(commands.Bot):
	def __init__(self, configFile):
		self.config = DiscordConfig(configFile)
		self.messages = queue.Queue()
		super(DiscordBot, self).__init__(self.config.commandPrefix, help_command=None)

	def startRunning(self):
		self.log('Starting the bot')
		self.run(self.config.token)

	async def listeningMessage(self):
		self.log('Message listening looping...')
		try:
			channel_chat = self.get_channel(self.config.channel_chat)
			while True:
				try:
					messageData = self.messages.get(block=False)  # type: MessageData
				except queue.Empty:
					await asyncio.sleep(0.05)
					continue
				self.log('Message data with type {} and channel {} get'.format(messageData.type, messageData.channel))
				data = messageData.data
				if messageData.type == MessageDataType.CHAT:  # chat message
					assert isinstance(data, dict)
					self.log('Processing chat message from chatbridge' + utils.messageData_to_string(data))
					for message in utils.messageData_to_strings(data):
						try:
							translation = translator.translate(data['message'], dest='en')
							dest = 'en'
							if translation.src != dest:
								message += '   | [{} -> {}] {}'.format(translation.src, dest, translation.text)
						except:
							self.log('Translate fail')
						await channel_chat.send(self.formatMessageToDiscord(message))
				elif messageData.type == MessageDataType.EMBED:  # embed
					assert isinstance(data, discord.Embed)
					self.log('Sending embed')
					await self.get_channel(messageData.channel).send(embed=data)
				elif messageData.type == MessageDataType.TEXT:
					await self.get_channel(messageData.channel).send(self.formatMessageToDiscord(str(data)))
				else:
					self.log('Unkown messageData type {}'.format(messageData.data))
		except:
			self.log(traceback.format_exc())
			await self.close()

	async def on_ready(self):
		self.log(f'Logged in as {self.user}')
		await self.listeningMessage()

	async def on_message(self, message):
		if message.author == self.user:
			return
		if message.channel.id in self.config.channels_command or message.channel.id == self.config.channel_chat:
			self.log(f"{message.channel}: {message.author}: {message.author.name}: {message.content}", log_to_file=False)
			args = message.content.split(' ')
			# Command
			if len(args) > 0 and args[0].startswith(self.config.commandPrefix):
				if message.channel.id in self.config.channels_command:
					await super(DiscordBot, self).on_message(message)
					if args[0] != '!!qq':
						return
			# Chat
			if message.channel.id == self.config.channel_chat:
				global chatClient
				chatClient.sendChatMessage(message.author.name, message.content)

	def addMessage(self, data, channel_id, t):
		self.messages.put(MessageData(data=data, channel=channel_id, type=t))

	def addResult(self, title, message, name, channel_id):
		def process_number(text):
			ret = x = int(text)
			for c in ['k', 'M']:
				if x < 1000:
					break
				x /= 1000
				ret = '%.{}f'.format(max(0, 4 - len(str(int(x))))) % x + c
			return str(ret)

		self.log('Adding result "' + str((title, message)) + '" to Discord Bot')
		msg = ''
		lines = self.formatMessageToDiscord(message).splitlines(keepends=True)
		message_len = len(lines)
		if message_len == 0:
			self.addMessage(title, channel_id, MessageDataType.TEXT)
			return
		if name == 'Stats Rank':  # the last line is "Total: xxx"
			message_len -= 1
		length = 0
		for i in range(message_len):
			msg += lines[i]
			length += len(lines[i])
			if i == message_len - 1 or length + len(lines[i + 1]) > 1024:
				embed = discord.Embed(color=discord.Colour.blue())
				embed.set_author(name=name, icon_url=EmbedIcon)
				if name == 'Stats Rank':
					rank = [line.split(' ')[0] for line in msg.splitlines()]
					player = [line.split(' ')[1] for line in msg.splitlines()]
					value = [process_number(line.split(' ')[2]) for line in msg.splitlines()]
					embed.add_field(name='Stats name', value=title, inline=False)
					embed.add_field(name='Rank', value='\n'.join(rank), inline=True)
					embed.add_field(name='Player', value='\n'.join(player), inline=True)
					embed.add_field(name='Value', value='\n'.join(value), inline=True)
					if i == message_len - 1:
						embed.set_footer(text='{} | {}'.format(lines[i + 1], process_number(lines[i + 1].split(' ')[-1])))  # "Total: xxx"
				else:
					embed.add_field(name=title, value=msg)
				self.log('Adding embed with length {} in message list'.format(len(msg)))
				self.addMessage(embed, channel_id, MessageDataType.EMBED)
				msg = ''
				length = 0

	@staticmethod
	def formatMessageToDiscord(msg):
		ret = msg
		for c in ['\\', '`', '*', '_', '<', '>', '@']:
			ret = ret.replace(c, '\\' + c)
		return ret

	@staticmethod
	def log(msg, log_to_file=True):
		msg = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time())) + ' [Discord] ' + msg
		print(msg)
		if log_to_file:
			utils.printLog(msg, LogFile)

def createDiscordBot():
	global discordBot
	discordBot = DiscordBot(DiscordConfigFile)

createDiscordBot()

@discordBot.command()
async def ping(ctx):
	await ctx.send('pong!!')

@discordBot.command()
async def online(ctx):
	if ctx.message.channel.id == discordBot.config.channel_chat:  # chat channel only
		command = '!!online'
		global chatClient
		if chatClient.isOnline:
			client = discordBot.config.clientToQueryOnline
			discordBot.log('Sending command "{}" to client {}'.format(command, client))
			chatClient.send_command_query(client, command, extra={'from_channel': ctx.message.channel.id})
		else:
			await ctx.send('ChatBridge client is offline')

StatsCommandHelpMessage = '''> `!!stats <classification> <target> [<-bot>] [<-all>]`
> add `-bot` to list bots (dumb filter tho)
> add `-all` to list every player (spam warning)
> example:
> `!!stats used diamond_pickaxe`
> `!!stats custom time_since_rest -bot`
'''
@discordBot.command()
async def stats(ctx, *args):
	command = '!!stats rank ' + ' '.join(args)
	if len(args) == 0 or len(args) - int(command.find('-bot') != -1) - int(command.find('-all') != -1) != 2:
		await ctx.send(StatsCommandHelpMessage)
		return
	global chatClient
	if chatClient.isOnline:
		client = discordBot.config.clientToQueryStats
		discordBot.log('Sending command "{}" to client {}'.format(command, client))
		chatClient.send_command_query(client, command, extra={'from_channel': ctx.message.channel.id})
	else:
		await ctx.send('ChatBridge client is offline')


CommandHelpMessage = '''
`!!help`: Display this message
`!!stats`: Show stats command help message
'''.strip()

# For chat channel, with full permission
CommandHelpMessageAll = CommandHelpMessage + '''
`!!online`: Show player list in online proxy
`!!qq <message>`: Send message `<message>` tp QQ group
'''.strip()


@discordBot.command()
async def help(ctx, *args):
	if ctx.message.channel.id == discordBot.config.channel_chat:
		text = CommandHelpMessageAll
	else:
		text = CommandHelpMessage
	await ctx.send(text)


class ChatClient(ChatBridge_client.ChatClient):
	def __init__(self, clientConfigFile):
		super(ChatClient, self).__init__(clientConfigFile, LogFile, ChatBridge_client.Mode.Discord)

	def on_recieve_message(self, data):
		global discordBot
		discordBot.addMessage(data, None, MessageDataType.CHAT)

	def on_recieve_command(self, data):
		result = data['result']
		if not result['responded']:
			return
		try:
			channel_id = data['extra']['from_channel']
		except:
			self.log('No channel id in command response data: {}'.format(data))
			return
		if data['command'].startswith('!!stats '):
			result_type = result['type']
			if result_type == 0:
				discordBot.addResult(result['stats_name'], result['result'], 'Stats Rank', channel_id)
			elif result_type == 1:
				discordBot.addMessage('Stats not found', channel_id, MessageDataType.TEXT)
			elif result_type == 2:
				discordBot.addMessage('StatsHelper plugin not loaded', channel_id, MessageDataType.TEXT)
		elif data['command'] == '!!online':
			result_type = result['type']
			if result_type == 0:
				discordBot.addResult('Player list', result['result'], 'TIS Online players', channel_id)
			elif result_type == 1:
				discordBot.addMessage('Online list query failed', channel_id, MessageDataType.TEXT)
			elif result_type == 2:
				discordBot.addMessage('Rcon is not working', channel_id, MessageDataType.TEXT)


def ChatBridge_guardian():
	global chatClient
	chatClient = ChatClient(ClientConfigFile)
	try:
		while True:
			if chatClient.isOnline() == False:
				chatClient.start()
			time.sleep(RetryTime)
	except (KeyboardInterrupt, SystemExit):
		chatClient.stop()
		exit(1)


if __name__ == '__main__':
	print('[ChatBridge] Discord Config File = ' + DiscordConfigFile)
	print('[ChatBridge] ChatBridge Client Config File = ' + ClientConfigFile)
	if not os.path.isfile(DiscordConfigFile) or not os.path.isfile(ClientConfigFile):
		print('[ChatBridge] Config File missing, exiting')
		exit(1)

	thread = threading.Thread(target=ChatBridge_guardian, args=())
	thread.setDaemon(True)
	thread.start()

	threshold = 0
	last_time = time.time()
	while True:
		threshold = threshold + RetryTime * 3 - (time.time() - last_time)
		if threshold < 0:
			threshold = 0
		last_time = time.time()
		if threshold >= RetryTime * 30:
			print('I have tried my best ...')
			break
		try:
			discordBot.startRunning()
		except (KeyboardInterrupt, SystemExit):
			chatClient.stop()
			break
		except:
			print(traceback.format_exc())
		time.sleep(RetryTime)
	#	discordBot = DiscordBot(DiscordConfigFile)

	print('Bye~')
