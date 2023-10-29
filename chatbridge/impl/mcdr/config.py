from typing import Optional

from chatbridge.core.config import ClientConfig


class MCDRClientConfig(ClientConfig):
	enable: bool = True
	debug: bool = False
	client_to_query_online: Optional[str] = None
