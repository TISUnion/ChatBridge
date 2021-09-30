# ChatBridge

Broadcast chat between Minecraft servers or even discord server

**[WARNING]** ChatBridge is mainly for TIS's custom use so expect  hardcoded constants

![topomap](https://raw.githubusercontent.com/TISUnion/ChatBridge/master/topomap.png)

## Usage

Python 3.6+ required

Enter `python -m ChatBridge.pyz` in command line to see possible helps

At launch, if the configure file is missing, chatbridge will automatically generate a default one and exit

## CLI Server

```
python -m ChatBridge.pyz server
```

Configure:

```json5
{
    "aes_key": "ThisIstheSecret",  // the common encrypt key for all clients
    "hostname": "localhost",  // the hostname of the server. Set it to "0.0.0.0" for general binding
    "port": 30001,  // the port of the server
    "clients": [  // a list of client
        {
            "name": "MyClientName",  // client name
            "password": "MyClientPassword"  // client password
        }
    ]
}
```

## CLI Client

```
python -m ChatBridge.pyz client
```

## [MCDReforged](https://github.com/Fallen-Breath/MCDReforged) plugin client

Required MCDR >=2.0

Just put the `.mcdr` file into the plugin folder

Configure:

```json5
{
    "aes_key": "ThisIstheSecret",  // the common encrypt key
    "name": "MyClientName",  // the name of the client
    "password": "MyClientPassword",  // the password of the client
    "server_hostname": "127.0.0.1",  // the hostname of the server
    "server_port": 30001  // the port of the server
}
```

## Discord bot client

`python -m ChatBridge.pyz discord_bot`

Extra requirements (also listed in `/chatbridge/impl/discord/requirements.txt`):

```
discord.py
google_trans_new
```

Extra configure fields (compared to CLI client)

```json5
    "bot_token": "your.bot.token.here",  // the token of your discord bot
    "channels_for_command": [  // a list of channels, public commands can be used here
        123400000000000000,
        123450000000000000
    ],
    "channel_for_chat": 123400000000000000,  // the channel for chatting and private commands
    "command_prefix": "!!",
    "client_to_query_stats": "MyClient1",  // it should be a client as an MCDR plugin, with stats_helper plugin installed in the MCDR
    "client_to_query_online": "MyClient2"  // a client described in the following section "Client to respond online command"
```

### Commands

`!!stats` will send command to `MyClient1` to query the StatsHelper plugin in the specific client for data

`!!online` will send command to `MyClient2` to use rcon to get `glist` command reply in bungeecord server

## Client as a CoolqHttp client

```
python -m ChatBridge.pyz cqhttp_bot
```

Extra requirements (also listed in `/cqhttp/impl/discord/requirements.txt`):

```
websocket
websocket-client
```

Needs any CoolQ Http protocol provider to work. e.g. [go-cqhttp](https://github.com/Mrs4s/go-cqhttp)

Due to lack of channel division in QQ group (not like discord), to prevent message spam player needs to use special command to let the bot recognize the message:

- In MC (othe client) use `!!qq <message>` to send message to QQ
- In QQ use `!!mc <message>` to send message

Type `!!help` in QQ for more help

Extra configure fields (compared to CLI client)

`ws_address`, `ws_port` and `access_token` are the same as the value in the config file of coolq-http-api

```json5
    "ws_address": "127.0.0.1",
    "ws_port": 6700,
    "access_token": "access_token.here",
    "react_group_id": 12345,  // the target QQ group id
    "client_to_query_stats": "MyClient1",  // it should be a client as an MCDR plugin, with stats_helper plugin installed in the MCDR
    "client_to_query_online": "MyClient2"  // a client described in the following section "Client to respond online command"
```

## Client to respond online command

```
python -m ChatBridge.pyz cqhttp_bot
```

Extra configure fields (compared to CLI client)

```json5
"bungeecord_list": [
    {
        "name": "BungeecordA",  // the name of the bungeecord server (unused value)
        "address": "127.0.0.1",  // the address of the bungeecord rcon
        "port": "3999",  // the port of the bungeecord rcon
        "password": "Bungee Rcon Password"  // the password of the bungeecord rcon
    }
]
```