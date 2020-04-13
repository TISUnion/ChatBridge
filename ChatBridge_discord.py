# -*- coding: UTF-8 -*-
import os
import json
import time
import asyncio
import threading
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
		self.channel = js['channel_id']
		self.commandPrefix = js['command_prefix']
		self.clientToQueryStats = js['client_to_query_stats']
		self.clientToQueryOnline = js['client_to_query_online']
		DiscordBot.log('Bot Token = ' + self.token)
		DiscordBot.log('Channel ID = ' + str(self.channel))
		DiscordBot.log('Command Prefix = ' + self.commandPrefix)
		DiscordBot.log('Client to Query !!stats = ' + self.clientToQueryStats)
		DiscordBot.log('Client to Query !!online = ' + self.clientToQueryOnline)

class DiscordBot(commands.Bot):
	messages = []
	def __init__(self, configFile):
		self.config = DiscordConfig(configFile)
		super(DiscordBot, self).__init__(self.config.commandPrefix)

	def startRunning(self):
		self.log('Starting the bot')
		self.run(self.config.token)

	async def listeningMessage(self):
		channel = self.get_channel(self.config.channel)
		try:
			while True:
				if len(self.messages) == 0:
					await asyncio.sleep(0.05)
					continue
				messageData = self.messages.pop(0)
				if type(messageData) == dict: # chat message
					self.log('Processing chat message ' + utils.messageData_to_string(messageData))
					for message in utils.messageData_to_strings(messageData):
						translation = translator.translate(messageData['message'], dest='en')
						dest = 'en'
						if translation.src != dest:
							message += '   | [{} -> {}] {}'.format(translation.src, dest, translation.text)
						await channel.send(self.formatMessageToDiscord(message))
				elif type(messageData) == discord.Embed: # embed
					await channel.send(embed=messageData)
				elif type(messageData) == str:
					await channel.send(self.formatMessageToDiscord(messageData))
				else:
					self.log('Unkown messageData type {}'.format(type(messageData)))
		except:
			s = traceback.format_exc()
			print(s)
			self.log(s)
			await self.close()

	async def on_ready(self):
		self.log(f'Logged in as {self.user}')
		await self.listeningMessage()

	async def on_message(self, message):
		if message.author == self.user or message.channel.id != self.config.channel:
			return
		if message.content.startswith(self.config.commandPrefix):
			await super(DiscordBot, self).on_message(message)
			return
		self.log(f"{message.channel}: {message.author}: {message.author.name}: {message.content}")
		global chatClient
		chatClient.sendChatMessage(message.author.name, message.content)

	def addChatMessage(self, messageData):
		self.log('Adding message "' + utils.messageData_to_string(messageData) + '" to Discord Bot')
		self.messages.append(messageData)

	def addMessage(self, message):
		self.messages.append(message)

	def addResult(self, title, message, name):
		message.replace('    ', ' ')
		self.log('Adding result "' + str((title, message)) + '" to Discord Bot')
		msg = ''
		lines = message.splitlines(keepends=True)
		length = 0
		for i in range(len(lines)):
			msg += self.formatMessageToDiscord(lines[i])
			length += len(lines[i])
			if i == len(lines) - 1 or length + len(lines[i + 1]) > 2048:
				embed = discord.Embed(
					title=title,
					description=msg,
					color=discord.Colour.blue()
				)
				embed.set_author(name=name, icon_url=EmbedIcon)
				self.messages.append(embed)
				msg = ''
				length = 0

	@staticmethod
	def formatMessageToDiscord(msg):
		ret = msg
		for c in ['\\', '`', '*', '_', '<', '>', '@']:
			ret = ret.replace(c, '\\' + c)
		return ret

	@staticmethod
	def log(msg):
		msg = time.strftime('[%Y-%m-%d %H:%M:%S]', time.localtime(time.time())) + ' [Discord] ' + msg
		print(msg)
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
	command = '!!online'
	global chatClient
	if chatClient.isOnline:
		client = discordBot.config.clientToQueryOnline
		discordBot.log('Sending command "{}" to client {}'.format(command, client))
		chatClient.send_command_query(client, command)
	else:
		await ctx.send('ChatBridge client is offline')

StatsCommandHelpMessage = '''> `!!stats <classification> <target> [<-bot>] [<-all>]`
> add `-bot` to list bots
> add `-all` to list every player
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
		chatClient.send_command_query(client, command)
	else:
		await ctx.send('ChatBridge client is offline')


class ChatClient(ChatBridge_client.ChatClient):
	def __init__(self, clientConfigFile):
		super(ChatClient, self).__init__(clientConfigFile, LogFile, ChatBridge_client.Mode.Discord)

	def on_recieve_message(self, data):
		global discordBot
		discordBot.addChatMessage(data)

	def on_recieve_command(self, data):
		result = data['result']
		if not result['responded']:
			return
		if data['command'].startswith('!!stats '):
			result_type = result['type']
			if result_type == 0:
				discordBot.addResult(result['stats_name'], result['result'], 'Stats Rank')
			elif result_type == 1:
				discordBot.addMessage('Stats not found')
			elif result_type == 2:
				discordBot.addMessage('StatsHelper plugin not loaded')
		elif data['command'] == '!!online':
			result_type = result['type']
			if result_type == 0:
				discordBot.addResult('Player list', result['result'], 'Online Proxy')
			elif result_type == 1:
				discordBot.addMessage('Online list query failed')
			elif result_type == 2:
				discordBot.addMessage('Rcon is not working')


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
