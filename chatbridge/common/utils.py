import time


def sleep():
	time.sleep(0.01)


def limited_length(s: str, limit: int = 48):
	limit = max(limit, 4)
	if len(s) <= limit:
		return s
	else:
		n = limit - 2
		x = int(n / 2)
		y = n - x
		return s[:x + 1] + '..' + s[len(s) - y:]


