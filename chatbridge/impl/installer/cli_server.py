import os
import shutil
import random
from random import randint
import json


# Main server of chat bridge
def cli_server(port, KEY, clients):
    print('-----------')
    print('cli server installation')
    path_cli = input('path to install CLI server executor: ')
    # check if directory is empty
    if not len(os.listdir(path_cli)) == 0:
        confirm = input('Directory not empty, do you want to install it anyway? [y/n]')
        if confirm.startswith('n') or confirm.startswith('N'):
            print('---------------------------')
            print('Finish of CLI configuration')
            print('---------------------------')
            return
    shutil.copyfile('./ChatBridge.pyz', path_cli+'/ChatBridge.pyz')  # Copy .pyz executable

    # Get the ip for cli
    cli_ip = input('IP for CLI server (default=127.0.0.1): ').replace(' ', '')
    if cli_ip == '': cli_ip = '127.0.0.1'
    
    # write the config
    cli_config = {"aes_key": KEY, "hostname": cli_ip, "port": port, "clients": clients, 
    "show_chat": True, "log_chat": False}
    with open(path_cli+'/ChatBridge_server.json', 'w') as f:
        f.write(json.dumps(cli_config, indent=2))
        f.close()
    print('---------------------------')
    print('Finish of CLI configuration')
    print('---------------------------')
