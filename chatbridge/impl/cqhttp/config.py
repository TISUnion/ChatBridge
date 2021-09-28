from chatbridge.core.config import ClientConfig


class CqHttpConfig(ClientConfig):
	ws_address: str
	ws_port: str
	access_token: str
	react_group_id: int
	client_to_query_stats: str = 'MyClient1'
	client_to_query_online: str = 'MyClient2'
