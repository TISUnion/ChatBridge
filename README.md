# ChatBridge
Broadcast chat between Minecraft servers or even discord server

`ChatBridge_lib.py` is the library of ChatBridge.

`ChatBridge_server.py` is the server

`ChatBridge_client.py` is the client. it can also be a mcd plugin

`ChatBridge_discord.py` will be a type of client that can control a discord bot

## Useage
`pip install pycrypto` for python 2

`pip install pycryptodome` for python 3

### Server

1. Grab `ChatBridgeLibrary/ChatBridge_lib.py` with its folder and `ChatBridge_server.py` in a folder
2. Create `ChatBridge_server.json` as the config file
3. Run `python ChatBridge_server.py`

`ChatBridge_server.json` format
```
{
	"aes_key": "theAESkey",
	"hostname": "0.0.0.0",
	"port": 23333,
	"clients":
	[
		{
			"name": "testClient",
			"password": "testPassword"
		},
		{
			"name": "SurvivalServer",
			"password": "_OwO_"
		},
		{
			"name": "DiscordBot",
			"password": "notvanilla"
		}
	]
}
```

### Client

1. Grab `ChatBridgeLibrary/ChatBridge_lib.py` with its folder and `ChatBridge_client.py` in a folder
2. Create `ChatBridge_client.json` as the config file
3. Run `python ChatBridge_client.py`

`ChatBridge_client.json` format
```
{
	"name": "testClient",
	"password": "testPassword",
	"server_hostname": "server.ChatBridge.orz",
	"server_port": 23333,
	"aes_key": "theAESkey"
}
```

The client will automatically start when the program starts

Type `start` to start the client and type `stop` to stop the client

### Client (as a [MCD](https://github.com/kafuuchino-desu/MCDaemon) plugin)

Compatible with  [MCDaemon](https://github.com/kafuuchino-desu/MCDaemon) and [MCDReforged](https://github.com/Fallen-Breath/MCDReforged)

1. Grab `ChatBridgeLibrary/ChatBridge_lib.py` with its folder and `ChatBridge_client.py` in `plugins/` folder
2. Create `config/ChatBridge_client.json` as the config file
3. Create `log/` folder if it doesn't exist
4. Run MCD

`ChatBridge_client.json` is exactly the same as above, but u can custom the displayed text color in it


### Client as a discord bot 

`pip install discord.py` first

**python3 only**

1. Grab `ChatBridgeLibrary/ChatBridge_lib.py` with its folder, `ChatBridge_client.py` and `ChatBridge_discord.py` in `plugins/` folder
2. Create `ChatBridge_client.json` and `ChatBridge_discord.json` as the config file
3. Run `python ChatBridge_discord.py`


`ChatBridge_client.json` is exactly the same as above, but u can custom the displayed text color in it

`ChatBridge_discord.json` format
```
{
	"bot_token": "your.bot.token.here",
	"channel_id": 645424523965046400
}
```