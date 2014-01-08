# Copyright 2013-4, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import saxo

@saxo.event("251")
def nickserv251(irc):
    if "plugins" in irc.config:
        if "nickserv" in irc.config["plugins"]:
            # Works on freenode, not sure about other servers. Easy to modify
            nick = irc.config["nick"]
            password = irc.config["plugins"]["nickserv"]
            irc.msg("NickServ", "IDENTIFY %s %s" % (nick, password))

@saxo.event("451")
def nickserv451(irc):
    if "plugins" in irc.config:
        if "nickserv" in irc.config["plugins"]:
            # Works on freenode, not sure about other servers. Easy to modify
            nick = irc.config["nick"]
            password = irc.config["plugins"]["nickserv"]
            irc.msg("NickServ", "IDENTIFY %s %s" % (nick, password))
