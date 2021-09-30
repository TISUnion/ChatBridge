from chatbridge.core.config import ClientConfig


class CqHttpConfig(ClientConfig):
	ws_address: str = '127.0.0.1'
	ws_port: int = 6700
	access_token: str = ''
	react_group_id: int = 12345
	client_to_query_stats: str = 'MyClient1'
	client_to_query_online: str = 'MyClient2'
