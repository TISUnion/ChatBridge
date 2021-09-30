import time
import traceback
from socket import socket
from threading import Thread


sock = socket()
Thread(target=lambda: (time.sleep(1), sock.close())).start()
try:
	sock.bind(('localhost', 54312))
	sock.listen(5)
	sock.accept()
except:
	traceback.print_exc()
print('end')

