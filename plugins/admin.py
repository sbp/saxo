# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import saxo

@saxo.command("quit")
def quit(irc):
    if "owner" in irc.config:
        if irc.prefix == irc.config["owner"]:
            irc.client("quit")

@saxo.command("reload")
def reload(irc):
    if "owner" in irc.config:
        if irc.prefix == irc.config["owner"]:
            irc.client("reload", irc.sender)
