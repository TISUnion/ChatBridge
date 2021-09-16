# -*- coding: UTF-8 -*-
import asyncio
import collections
import json
import os
import queue
import threading
import time
import traceback
from enum import Enum
from typing import Optional, NamedTuple, Any

import discord
from discord.ext import commands

from chatbridge.impl import utils
from chatbridge.impl.discord import stored, bot
from chatbridge.impl.discord.client import DiscordChatClient
from chatbridge.impl.discord.config import DiscordConfig

ConfigFile = 'ChatBridge_client.json'


def ChatBridge_guardian():
	try:
		while True:
			if not stored.client.is_online():
				stored.client.start()
			time.sleep(3)
	except (KeyboardInterrupt, SystemExit):
		stored.client.stop()
		exit(1)


def main():
	stored.config = utils.load_config(ConfigFile, DiscordConfig)
	stored.bot = bot.create_bot()
	stored.client = DiscordChatClient(stored.config)


if __name__ == '__main__':
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
			bot.startRunning()
		except (KeyboardInterrupt, SystemExit):
			chatClient.stop()
			break
		except:
			print(traceback.format_exc())
		time.sleep(RetryTime)

	print('Bye~')
