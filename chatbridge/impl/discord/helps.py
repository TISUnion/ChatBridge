CommandHelpMessage = '''
`!!help`: Display this message
`!!stats`: Show stats command help message
'''.strip()

# For chat channel, with full permission
CommandHelpMessageAll = CommandHelpMessage + '\n' + '''
`!!online`: Show player list in online proxy
`!!qq <message>`: Send message `<message>` to QQ group
'''.strip()

StatsCommandHelpMessage = '''
`!!stats <classification> <target> [<-bot>] [<-all>]`
add `-bot` to list bots (dumb filter tho)
add `-all` to list every player (spam warning)
`<classification>`: `killed`, `killed_by`, `dropped`, `picked_up`, `used`, `mined`, `broken`, `crafted`, `custom`
the `<target>` of `killed`, `killed_by` are entity type
the `<target>` of `picked_up`, `used`, `mined`, `broken`, `crafted` are block/item id
for the `<target>` of `custom` or more info, check https://minecraft.gamepedia.com/Statistics
Example:
`!!stats used diamond_pickaxe`
`!!stats custom time_since_rest -bot`
'''.strip()
