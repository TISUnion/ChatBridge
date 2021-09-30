from typing import List

from mcdreforged.utils.serializer import Serializable


class StatsQueryResult(Serializable):
	error_code: int = 0
	stats_name: str
	data: List[str]
	total: int

	@property
	def success(self) -> bool:
		return self.error_code == 0

	@classmethod
	def create(cls, stats_name: str, data: List[str], total: int) -> 'StatsQueryResult':
		return StatsQueryResult(error_code=0, stats_name=stats_name, data=data, total=total)

	@classmethod
	def unknown_stat(cls) -> 'StatsQueryResult':
		return StatsQueryResult(error_code=1)

	@classmethod
	def no_plugin(cls) -> 'StatsQueryResult':
		return StatsQueryResult(error_code=2)


class OnlineQueryResult(Serializable):
	data: List[str]

	@classmethod
	def create(cls, data: List[str]) -> 'OnlineQueryResult':
		return OnlineQueryResult(data=data)
