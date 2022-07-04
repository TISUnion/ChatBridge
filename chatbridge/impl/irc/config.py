from typing import List

from chatbridge.core.config import ClientConfig

class IRCConfig(ClientConfig):
	ircserver: str = "your.server.here"
	ircport: int = 6667
	channel: str =  '#channel'
	nickname: str = 'bot1'
	ircpassword: str = ''
	nickserv: str = 'NickServ'
	nickservauth: str = 'IDENTIFY Password'
	nickservaskpass: str = '/msg NickServ IDENTIFY'
	nickservsuccess: str = 'Password accepted'