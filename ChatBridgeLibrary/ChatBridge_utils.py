# coding: utf8

import os
import sys


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

def printLog(msg, logFileName):
	try:
		msg = toUTF8(msg)
		if not os.path.isfile(logFileName):
			with open(logFileName, 'w') as f:
				pass
		with open(logFileName, 'a') as logfile:
			logfile.write(stringAdd(msg, '\n'))
	except IOError:
		print('Fail to access log file "', logFileName, '"')


# for python2 stuffs
def toUTF8(str):
	if sys.version_info.major == 3:
		return str
	return str.encode('utf-8') if type(str).__name__ == 'unicode' else str


def stringAdd(a, b):
	return toUTF8(a) + toUTF8(b)


def addressToString(addr):
	return '{0}:{1}'.format(addr[0], addr[1])
