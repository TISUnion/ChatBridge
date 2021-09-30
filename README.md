# ChatBridge

Broadcast chat between Minecraft servers or even discord server

**[WARNING]** ChatBridge is mainly for TIS's custom use so expect  hardcoded constants

![topomap](https://raw.githubusercontent.com/TISUnion/ChatBridge/master/topomap.png)

## Usage

Python 3.6+ required

Enter `python -m ChatBridge-*.mcdr` in command line to see possible helps

## CLI Server

```
python -m ChatBridge-*.mcdr server
```

## CLI Client

```
python -m ChatBridge-*.mcdr client
```

## [MCDReforged](https://github.com/Fallen-Breath/MCDReforged) plugin client

Required MCDR >=2.0

Just put the `.mcdr` file into the plugin folder

## Discord bot client

`python -m ChatBridge-*.mcdr discord_bot`

Extra requirements (also listed in `/chatbridge/impl/discord/requirements.txt`):

```
discord.py
google_trans_new
```

### Commands

`!!stats` will send command to `MyClient1` to query the StatsHelper plugin in the specific client for data

`!!online` will send command to `MyClient2` to use rcon to get `glist` command reply in bungeecord server

## Client as a CoolqHttp client

```
python -m ChatBridge-*.mcdr cqhttp_bot
```

Extra requirements (also listed in `/cqhttp/impl/discord/requirements.txt`):

```
websocket
websocket-client
```

Needs any CoolQ Http protocol provider to work. e.g. [go-cqhttp](https://github.com/Mrs4s/go-cqhttp)

`ws_address`, `ws_port` and `access_token` are the same as the value in the config file of coolq-http-api

Due to lack of channel division in QQ group (not like discord), to prevent message spam player needs to use special command to let the bot recognize the message:

- In MC (othe client) use `!!qq <message>` to send message to QQ
- In QQ use `!!mc <message>` to send message

Type `!!help` in QQ for more help

## Client to response online command

```
python -m ChatBridge-*.mcdr cqhttp_bot
```
