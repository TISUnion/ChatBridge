import time


def messageData_to_strings(data):
	client = toUTF8(data['client'])
	player = toUTF8(data['player'])
	message = toUTF8(data['message'])
	ret = []
	for line in message.splitlines():
		if player != "":
			ret.append('[{}] <{}> {}'.format(client, player, line))  # chat message
		else:
			ret.append('[{}] {}'.format(client, line))  # player login message or others
	return ret


def commandData_to_string(data):
	sender = toUTF8(data['sender'])
	receiver = toUTF8(data['receiver'])
	command = toUTF8(data['command'])
	result = toUTF8(data['result'])
	if not result['responded']:
		ret = '[{} -> {}] {}'.format(sender, receiver, command)
	else:
		ret = '[{} <- {}] {} | {}'.format(sender, receiver, command, limited_length(str(result)))
	return ret


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


