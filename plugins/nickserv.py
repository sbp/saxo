# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import saxo

@saxo.event("001")
def nickserv(irc):
    if "nickserv" in irc.config:
        # Works on freenode, not sure about other servers. Easy to modify
        nick = irc.config["nick"]
        password = irc.config["plugins"]["nickserv"]
        irc.msg("NickServ", "IDENTIFY %s %s" % (nick, password))
