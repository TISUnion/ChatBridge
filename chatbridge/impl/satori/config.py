from chatbridge.core.config import ClientConfig


class SatoriConfig(ClientConfig):
	ws_address: str = '127.0.0.1'
	ws_port: int = 6700
	ws_path: str = ''
	satori_token: str = ''
	react_channel_id: int = 12345
	chatbridge_message_prefix: str = '!!qq'
	client_to_query_stats: str = 'MyClient1'
	client_to_query_online: str = 'MyClient2'
