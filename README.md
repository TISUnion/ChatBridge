# ChatBridge

Broadcast chat between Minecraft servers or even discord server

**[WARNING]** ChatBridge is mainly for TIS's custom use so expect messy code structures and hardcoded constants

`ChatBridge_lib.py` and `ChatBridge_utils.py` are the library of ChatBridge

`ChatBridge_server.py` is the server

`ChatBridge_client.py` is the client. it can also be a mcd plugin

`ChatBridge_discord.py` will be a type of client that can control a discord bot

![topomap](https://raw.githubusercontent.com/TISUnion/ChatBridge/master/topomap.png)

## Useage

`pip install pycrypto` for python 2

`pip install pycryptodome` for python 3

### Server

1. Grab `ChatBridgeLibrary/ChatBridge_lib.py` and `ChatBridgeLibrary/ChatBridge_utils.py` with their folder and `ChatBridge_server.py` in a folder
2. Create `ChatBridge_server.json` as the config file
3. Run `python ChatBridge_server.py`

```
MyFolder
├─ ChatBridgeLibrary
│ ├─ ChatBridge_lib.py
│ └─ ChatBridge_utils.py
├─ ChatBridge_server.py
└─ ChatBridge_server.json
```

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

1. Grab `ChatBridgeLibrary/ChatBridge_lib.py` and `ChatBridgeLibrary/ChatBridge_utils.py` with their folder and `ChatBridge_client.py` in a folder
2. Create `ChatBridge_client.json` as the config file
3. Run `python ChatBridge_client.py`

```
MyFolder
├─ ChatBridgeLibrary
│ ├─ ChatBridge_lib.py
│ └─ ChatBridge_utils.py
├─ ChatBridge_client.py
└─ ChatBridge_client.json
```

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

1. Grab `ChatBridgeLibrary/ChatBridge_lib.py` and `ChatBridgeLibrary/ChatBridge_utils.py` with their folder and `ChatBridge_client.py` into `plugins` folder
2. Create `config/ChatBridge_client.json` as the config file
3. Create `log/` folder if it doesn't exist
4. Run MCD

`ChatBridge_client.json` is exactly the same as above, but u can custom the displayed text color in it

```
MCDaemon
├─ plugins
│ ├─ ChatBridgeLibrary
│ │ ├─ ChatBridge_lib.py
│ │ └─ ChatBridge_utils.py
│ └─ ChatBridge_client.py
│─ config
| └─ ChatBridge_client.json
└─ ...
```

### Client as a discord bot 

**python3 only**

`pip install discord.py googletrans` first

1. Grab `ChatBridgeLibrary/ChatBridge_lib.py` with its folder, `ChatBridge_client.py` and `ChatBridge_discord.py` in `plugins/` folder
2. Create `ChatBridge_client.json` and `ChatBridge_discord.json` as the config file
3. Run `python ChatBridge_discord.py`

`ChatBridge_client.json` is exactly the same as above, but u can custom the displayed text color in it

```
MyFolder
├─ ChatBridgeLibrary
│ ├─ ChatBridge_lib.py
│ └─ ChatBridge_utils.py
├─ ChatBridge_discord.py
├─ ChatBridge_discord.json
└─ ChatBridge_client.json
```

`ChatBridge_discord.json` format
```
{
	"bot_token": "your.bot.token.here",
	"channel_id": 645424523965046400,
	"command_prefix": "!!",
	"client_to_query_stats": "MyClient1",
	"client_to_query_online": "MyClient2"
}
```

`!!stats` will send command to `MyClient1` to query the StatsHelper plugin in the specific client for data

`!!online` will send command to `MyClient2` to use rcon to get `glist` command reply in bungeecord server

### Client as a CooqHttp client

**python3 only**

~~Needs [coolq-http-api](https://github.com/richardchien/coolq-http-api) server running~~ (:ghost: it's down)

Needs any CoolQ Http protocol provider to work. e.g. [go-cqhttp](https://github.com/Mrs4s/go-cqhttp)

`pip install websocket websocket-client` first

1. Grab `ChatBridgeLibrary/ChatBridge_lib.py` with its folder, `ChatBridge_client.py` and `ChatBridge_discord.py` in `plugins/` folder
2. Create `ChatBridge_client.json` and `ChatBridge_CQHttp.json` as the config file
3. Open CoolQ with coolq-http-api enabled, then close it
4. Open `CoolQ/data/app/io.github.richardchien.coolqhttpapi/config/<your_qq_id>.json`, set `use_ws` to `true` and set your `access_token`. You can also set `use_http` to `false` since it's not necessary
4. Run `python ChatBridge_cqhttp.py`

`ChatBridge_client.json` is exactly the same as above, but u can custom the displayed text color in it

```
MyFolder
├─ ChatBridgeLibrary
│ ├─ ChatBridge_lib.py
│ └─ ChatBridge_utils.py
├─ ChatBridge_CQHttp.py
├─ ChatBridge_CQHttp.json
└─ ChatBridge_client.json
```

`ChatBridge_CQHttp.json` format

```
{
	"ws_address": "127.0.0.1",
	"ws_port": 6700,
	"access_token": "my_access_token",
	"react_group_id": 138150445
}
```

`ws_address`, `ws_port` and `access_token` are the same as the value in the config file of coolq-http-api


In MC use `!!qq <message>` to send message

In QQ use `!!mc <message>` to send message

Type `!!help` in QQ for more help
