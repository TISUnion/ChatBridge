import os
import shutil
from random import randint
import json


# Main server of chat bridge
def mc_server(port, KEY):
    print('-----------')
    print('mcdr server installation')
    path_cli = input('path of root mcdr server: ')

    shutil.copyfile('./ChatBridge.pyz', path_cli+'/plugins/ChatBridge.pyz')  # Copy .pyz executable

    # ask stuff
    mcdr_ip = input('IP for CLI server (default=127.0.0.1): ').replace(' ', '')
    if mcdr_ip == '': mcdr_ip = '127.0.0.1'
    name_mcdr = input('name of server: ')
    mcdr_password = input('password for mcdr server: ')

    # write the config
    mcdr_config = {"aes_key": KEY, "name": name_mcdr, "password": mcdr_password, "server_hostname": mcdr_ip, "server_port": port, "debug": False}
    try:
        os.mkdir(path_cli+'/config/chatbridge')
    except FileExistsError:
        pass
    with open(path_cli+'/config/chatbridge/config.json', 'w') as f:
        f.write(json.dumps(mcdr_config, indent=2))
        f.close()
    print('----------------------------')
    print('Finish of mcdr configuration')
    print('----------------------------')
    return {"name": name_mcdr, "password": mcdr_password}
