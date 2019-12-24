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
		self.clientToQuery = js['client_to_query']
		DiscordBot.log('Bot Token = ' + self.token)
		DiscordBot.log('Channel ID = ' + str(self.channel))
		DiscordBot.log('Command Prefix = ' + self.commandPrefix)
		DiscordBot.log('Client to Query = ' + self.clientToQuery)

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
				if type(messageData).__name__ == 'dict': # chat message
					self.log('Processing chat message ' + utils.messageData_to_string(messageData))
					for message in utils.messageData_to_strings(messageData):
						translation = translator.translate(messageData['message'], dest='en')
						if translation.src != 'en':
							message += '   | [en] ' + translation.text
						await channel.send(self.formatMessageToDiscord(message))
				elif type(messageData).__name__ == 'Embed': # embed
					await channel.send(embed=messageData)
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

	def addMessage(self, messageData):
		self.log('Adding message "' + utils.messageData_to_string(messageData) + '" to Discord Bot')
		self.messages.append(messageData)

	def addResult(self, title, message):
		message.replace('    ', ' ')
		self.log('Adding result "' + str((title, message)) + '" to Discord Bot')
		msg = ''
		lines = message.splitlines(keepends=True)
		length = 0
		for i in range(len(lines)):
			msg += lines[i]
			length += len(lines[i])
			if i == len(lines) - 1 or length + len(lines[i + 1]) > 2048:
				embed = discord.Embed(
					title=title,
					description=msg,
					color=discord.Colour.blue()
				)
				embed.set_author(name='Stats Rank', icon_url=EmbedIcon)
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


discordBot = DiscordBot(DiscordConfigFile)

@discordBot.command()
async def ping(ctx):
	await ctx.send('pong!!')

@discordBot.command()
async def online(ctx):
	pass

StatsCommandHelpMessage = '''> `!!stats <classification> <target> [<-bot>] [<-all>]`
> add `-bot` to list bots
> add `-all` to every player
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
		client = discordBot.config.clientToQuery
		discordBot.log('Sending command "{}" to client {}'.format(command, client))
		chatClient.send_command(client, command)
	else:
		await ctx.send('ChatBridge client is offline')


class ChatClient(ChatBridge_client.ChatClient):
	lastMessageReceivedTime = None
	def __init__(self, clientConfigFile):
		super(ChatClient, self).__init__(clientConfigFile, LogFile, ChatBridge_client.Mode.Discord)

	def on_recieve_message(self, data):
		global discordBot
		discordBot.addMessage(data)
		self.lastMessageReceivedTime = time.time()

	def on_recieve_command(self, data):
		result = DiscordBot.formatMessageToDiscord(data['result'])
		lines = result.splitlines()
		title = lines[0]
		lines = lines[1:]
		if result != lib.CommandNoneResult:
			discordBot.addResult(title, '\n'.join(lines))

	def start(self):
		self.lastMessageReceivedTime = time.time()
		super(ChatClient, self).start(None)

	def getLastMessageReceivedTime(self):
		return self.lastMessageReceivedTime


def ChatBridge_guardian():
	global chatClient
	chatClient = ChatClient(ClientConfigFile)
	try:
		while True:
			if chatClient.isOnline() == False:
				chatClient.start()
			if time.time() - chatClient.getLastMessageReceivedTime() > 3600 * 3: # 3h
				chatClient.stop(True)
			time.sleep(RetryTime)
	except (KeyboardInterrupt, SystemExit):
		chatClient.stop(True)
		exit(1)


print('[ChatBridge] Discord Config File = ' + DiscordConfigFile)
print('[ChatBridge] ChatBridge Client Config File = ' + ClientConfigFile)
if not os.path.isfile(DiscordConfigFile) or not os.path.isfile(ClientConfigFile):
	print('[ChatBridge] Config File missing, exiting')
	exit(1)

thread = threading.Thread(target=ChatBridge_guardian, args=())
thread.setDaemon(True)
thread.start()

while True:
	try:
		discordBot.startRunning()
	except (KeyboardInterrupt, SystemExit):
		chatClient.stop(True)
		break
	except:
		pass
	time.sleep(RetryTime)
#	discordBot = DiscordBot(DiscordConfigFile)