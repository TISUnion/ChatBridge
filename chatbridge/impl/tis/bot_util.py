from typing import Union


def process_number(text: Union[str, int]) -> str:
	ret = x = int(text)
	for c in ['k', 'M', 'B']:
		if x < 1000:
			break
		x /= 1000
		ret = '%.{}f'.format(max(0, 4 - len(str(int(x))))) % x + c
	return str(ret)
