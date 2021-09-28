from mcdreforged.api.utils.serializer import Serializable


class NoMissingSerializable(Serializable):
	@classmethod
	def deserialize(cls, data: dict, **kwargs):
		kwargs.setdefault('error_at_missing', True)
		return super().deserialize(data, **kwargs)

	@classmethod
	def get_default(cls):
		return cls.deserialize({}, error_at_missing=False)
