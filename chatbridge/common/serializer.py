from typing import TypeVar, Type

from mcdreforged.api.utils.serializer import Serializable

Self = TypeVar('Self', bound='NoMissingFieldSerializable')


class NoMissingFieldSerializable(Serializable):
	@classmethod
	def deserialize(cls: Type[Self], data: dict, **kwargs) -> Self:
		kwargs.setdefault('error_at_missing', True)
		# noinspection PyTypeChecker
		return super().deserialize(data, **kwargs)

	@classmethod
	def get_default(cls):
		return cls.deserialize({}, error_at_missing=False)
