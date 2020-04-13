# coding: utf8
import codecs
import os
import sys
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

def messageData_to_string(data):
	return '\n'.join(messageData_to_strings(data))

def commandData_to_string(data):
	sender = toUTF8(data['sender'])
	receiver = toUTF8(data['receiver'])
	command = toUTF8(data['command'])
	result = toUTF8(data['result'])
	if not result['responded']:
		ret = '[{} -> {}] {}'.format(sender, receiver, command)
	else:
		ret = '[{} <- {}] {} | {}'.format(sender, receiver, command, lengthLimit(str(result)))
	return ret

def printLog(msg, logFileName):
	try:
		msg = toUTF8(msg)
		if not os.path.isfile(logFileName):
			with open(logFileName, 'w') as f:
				pass
		with codecs.open(logFileName, 'a', encoding='utf8') as logfile:
			logfile.write(stringAdd(msg, '\n'))
	except IOError:
		print('Fail to access log file "', logFileName, '"')

def sleep():
	time.sleep(0.01)

def lengthLimit(str, limit=48):
	limit = max(limit, 4)
	if len(str) <= limit:
		return str
	else:
		n = limit - 2
		x = int(n / 2)
		y = n - x
		return str[:x + 1] + '..' + str[len(str) - y:]


# for python2 stuffs

def toUTF8(str):
	if sys.version_info.major == 3:
		return str
	return str.encode('utf-8') if type(str).__name__ == 'unicode' else str


def stringAdd(a, b):
	return toUTF8(a) + toUTF8(b)


def addressToString(addr):
	return '{0}:{1}'.format(addr[0], addr[1])
