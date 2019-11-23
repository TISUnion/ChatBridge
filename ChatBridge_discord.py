# -*- coding: UTF-8 -*-

import discord
import os
import json
import time
import asyncio
import threading
import ChatBridge_client
from ChatBridgeLibrary.ChatBridge_lib import printLog

DiscordConfigFile = 'ChatBridge_discord.json'
ClientConfigFile = 'ChatBridge_client.json'
LogFile = 'ChatBridge_discord.log'
RetryTime = 3 # second

class DiscordConfig():
	def __init__(self, configFile):
		js = json.load(open(configFile, 'r'))
		self.token = js['bot_token']
		self.channel = js['channel_id']
		log('[Discord] Bot Token = ' + self.token)
		log('[Discord] Channel ID = ' + str(self.channel))


class DiscordClient(discord.Client):
	messages = []
	def __init__(self, configFile):
		self.config = DiscordConfig(configFile)
		super(DiscordClient, self).__init__()

	def startRunning(self):
		log('Starting the bot')
		self.run(self.config.token)

	async def on_ready(self):
		log(f'Logged in as {self.user}')

		channel = self.get_channel(self.config.channel)
		while True:
			if len(self.messages) == 0:
				await asyncio.sleep(0.3)
				continue
			msg = self.messages.pop(0)
			await channel.send(self.formatMessageToDiscord(msg))

	async def on_message(self, message):
		if message.author == self.user or message.channel.id != self.config.channel:
			return
		log(f"{message.channel}: {message.author}: {message.author.name}: {message.content}")
		global chatClient
		for line in message.content.splitlines():
			chatClient.sendMessage(self.formatMessageToMinecraft(message.author.name, line))
			await asyncio.sleep(0.1)

	def addMessage(self, msg):
		log('Adding message "' + msg + '" to Discord Bot')
		self.messages.append(msg)

	@staticmethod
	def formatMessageToDiscord(msg):
		ret = msg
		for c in ['\\', '`', '*', '_']:
			ret = ret.replace(c, '\\' + c)
		return ret

	@staticmethod
	def formatMessageToMinecraft(name, msg):
		return '<' + name + '> ' + msg


class ChatClient(ChatBridge_client.ChatClient):
	lastMessageReceivedTime = None
	def __init__(self, clientConfigFile):
		super(ChatClient, self).__init__(clientConfigFile, LogFile, ChatBridge_client.Mode.Discord)

	def recieveMessage(self, msg):
		global discordBot
		discordBot.addMessage(msg)
		lastMessageReceivedTime = time.time()

	def start(self):
		self.lastMessageReceivedTime = time.time()
		super(ChatClient, self).start(None)

	def getLastMessageReceivedTime(self):
		return self.lastMessageReceivedTime


def log(msg):
	msg = '[Discord] ' + msg
	print(msg)
	printLog(msg, LogFile)

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
	discordBot = DiscordClient(DiscordConfigFile)
	try:
		discordBot.startRunning()
	except (KeyboardInterrupt, SystemExit):
		chatClient.stop(True)
		break
	except:
		pass
	time.sleep(RetryTime)