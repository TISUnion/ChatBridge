# ChatBridge
Broadcast chat between mc servers or even discord server

`ChatBridge_lib.py` is the library of ChatBridge.

`ChatBridge_server.py` is the server

`ChatBridge_client.py` is the client. it can also be a mcd plugin

[WIP] `ChatBridge_discord.py` will be the client that controls a discord bot

## Useage
`pip install pycrypto` for python 2

`pip install pycryptodome` for python 3

### Server

1. Grab `ChatBridge_lib.py` and `ChatBridge_server.py` in a folder
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
		}
	]
}
```

### Client

1. Grab `ChatBridge_lib.py` and `ChatBridge_client.py` in a folder
2. Create `ChatBridge_client.json` as the config file
3. Run `python ChatBridge_client.py`

`ChatBridge_server.json` format
```
{
	"name": "testClient",
	"password": "testPassword",
	"server_hostname": "ChatBridge.server",
	"server_port": 23333,
	"aes_key": "theAESkey"
}
```

The client will automatically start when the program starts

Type `start` to start the client and type `stop` to stop the client

### Client (as a [MCD](https://github.com/kafuuchino-desu/MCDaemon) plugin)

1. Grab `ChatBridge_lib.py` and `ChatBridge_client.py` in `plugins/` folder
2. Create `config/ChatBridge_client.json` as the config file
3. Create `log/` folder if it doesn't exist
4. Run MCD


`ChatBridge_server.json` is exactly the same as above, but u can custom the displayed text color in it
```
{
	"name": "SurvivalServer",
	"password": "_OwO_",
	"server_hostname": "localhost",
	"server_port": 23333,
	"aes_key": "theAESkey",
	"color": "§7"
}
```

