import random
from random import randint

from chatbridge.impl.installer.discord import discord
from chatbridge.impl.installer.mc_server import mc_server
from chatbridge.impl.installer.cli_server import cli_server

# Declare some global variables for config
clients = []
used_port = [e for e in range(30)]+[443, 80, 8080, None]


# Main function
def install():
    print("-------------------------------")
    print("| ChatBridge Installer by: luisch444")
    print("| You can ask me: discord luisch444#3512")
    print("-------------------------------")
    print("""Module to install:
1. discord
2. CQHttp **not available**
3. Kaiheila **not available**
example: 13""")
    options = input()
    
    print("""Set ports (default=[30001-31000])
You can separate by commas (random): 30001, 30002, 30003
You can use ranges example (random): 30001-31000
You can set it manually example: 30001""")
    # port config stuff 
    # I missed up here because I think that was multiple ports but anyway this work
    ports = input().replace(' ', '').split(',')
    port_configuration = {"port_min": [], "port_max": [], "ports": [], "custom_ports": {}}
    if '' in ports:
        port_configuration['port_min'].append(30001)
        port_configuration['port_max'].append(31000)
    else:
        for p in ports:
            if '-' in p:
                set_port = p.split('-')
                port_configuration['port_min'].append(int(set_port[0]))
                port_configuration['port_max'].append(int(set_port[1]))
            elif '=' in p:
                set_port = p.split('=')
                port_configuration['custom_ports'][set_port[0]] = int(set_port[1])
            else:
                port_configuration['ports'].append(int(p))
    print(str(port_configuration))
    if (port:=port_configuration['custom_ports'].get('mcdr_server')) is None:
        while port in used_port: port = random.choice([randint(port_configuration['port_min'][r], 
        port_configuration['port_max'][r]) for r in range(len(port_configuration['port_max']))]+port_configuration['ports'])
    print('Using port '+str(port))

    # the important key
    global KEY 
    KEY = input('Main key (AES): ')
    if KEY == '': KEY = 'SUS'
    # install all
    for i in range(len(str(options))+1):
        print(i)
        if i==1:
            msg = 'Install discord bot [y/n] '
            count = 1
            while not input(msg).lower().startswith('n'):
                msg = 'Intall another discord bot [y/n] '
                clients.append(discord(port, count, KEY))
                count+=1
        elif i==2:
            # CQHttp server config
            pass
        elif i==3:
            # Kaiheila server config
            pass
    msg = ''
    while not msg.lower().startswith('n'):
        clients.append(mc_server(port, KEY))
        msg = input('Add another mcdr server [y/n] ')
    cli_server(port, KEY, clients)
