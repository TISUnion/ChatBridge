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
				await asyncio.sleep(0.5)
				continue
			msg = self.messages.pop(0)
			await channel.send(msg)

	async def on_message(self, message):
		if message.author == self.user or message.channel.id != self.config.channel:
			return
		log(f"{message.channel}: {message.author}: {message.author.name}: {message.content}")
		global chatClient
		chatClient.sendMessage('<' + message.author.name + '> ' + message.content)

	def addMessage(self, msg):
		log('Adding message "' + msg + '" to Discord Bot')
		self.messages.append(msg)


class ChatClient(ChatBridge_client.ChatClient):
	def __init__(self, clientConfigFile):
		super(ChatClient, self).__init__(clientConfigFile, LogFile, ChatBridge_client.Mode.Discord)

	def recieveMessage(self, msg):
		global discordBot
		discordBot.addMessage(msg)


def log(msg):
	msg = '[Discord] ' + msg
	print(msg)
	printLog(msg, LogFile)

def ChatBridge_guardian():
	global chatClient
	chatClient = ChatClient(ClientConfigFile)
	while True:
		if chatClient.isOnline() == False:
			chatClient.start(None)
		time.sleep(RetryTime)


print('[ChatBridge] Discord Config File = ' + DiscordConfigFile)
print('[ChatBridge] ChatBridge Client Config File = ' + ClientConfigFile)
if not os.path.isfile(DiscordConfigFile) or not os.path.isfile(ClientConfigFile):
	print('[ChatBridge] Config File missing, exiting')
	exit(1)


thread = threading.Thread(target=ChatBridge_guardian, args=())
thread.setDaemon(True)
thread.start()

discordBot = DiscordClient(DiscordConfigFile)
try:
	discordBot.startRunning()
except (KeyboardInterrupt, SystemExit):
	chatClient.stop(True)
