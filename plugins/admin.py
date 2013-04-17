# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import saxo

@saxo.command("quit")
def quit(irc):
    if "owner" in irc.client:
        if irc.prefix == irc.client["owner"]:
            irc.queue(("quit",))

@saxo.command("reload")
def reload(irc):
    if "owner" in irc.client:
        if irc.prefix == irc.client["owner"]:
            irc.queue(("reload", irc.sender))
