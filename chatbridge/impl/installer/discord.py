import os
import shutil
import random
from random import randint
import json


# Discord installation
def discord(port, n, KEY):
    print('-----------')
    print('discord installation')
    path_dc = input('path to install discord executor: ')
    # check if directory is empty
    if not len(os.listdir(path_dc)) == 0:
        confirm = input('Directory not empty, do you want to install it anyway? [y/n]')
        if confirm.startswith('n') or confirm.startswith('N'):
            print('-------------------------------')
            print('Finish of discord configuration')
            print('-------------------------------')
            return
    shutil.copyfile('./ChatBridge.pyz', path_dc+'/ChatBridge.pyz')  # Copy .pyz executable


    # asking stuff
    dc_token = input('paste your bot token: ')
    dc_ip = input('IP for discord (default=127.0.0.1): ').replace(' ', '')
    if dc_ip == '': dc_ip = '127.0.0.1'
    dc_password = input('password for discord: ')
    dc_chat = input('channel for chatbridge: ')
    dc_prefix = input ('Bot prefix: ')

    # and write the config
    dc_config = {"aes_key": KEY, "name": f"discord{str(n)}", "password": dc_password, 
    "server_hostname": dc_ip, "server_port": port, "bot_token": dc_token, 
    "channels_for_command": [], "channel_for_chat": int(dc_chat), "command_prefix": dc_prefix, 
    "server_display_name": "discord"+str(n)}
    with open(path_dc+'/ChatBridge_discord.json', 'w') as f:
        f.write(json.dumps(dc_config, indent=2))
        f.close()
    print('-------------------------------')
    print('Finish of discord configuration')
    print('-------------------------------')
    return {"name": f"discord{str(n)}", "password": dc_password}
