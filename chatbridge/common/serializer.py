from mcdreforged.api.utils.serializer import Serializable as mcdr_Serializable


class Serializable(mcdr_Serializable):
	@classmethod
	def deserialize(cls, data: dict, **kwargs):
		if 'error_at_missing' not in kwargs:
			kwargs['error_at_missing'] = True
		return super().deserialize(data)

	@classmethod
	def get_default(cls):
		return cls.deserialize({}, error_at_missing=False)
