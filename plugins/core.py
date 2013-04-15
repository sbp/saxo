# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import saxo

@saxo.event(":1st")
def connected(irc):
    irc.send("NICK", irc.client["nick"])
    irc.send("USER", irc.client["nick"], "+iw", irc.client["nick"], "saxo")
    for channel in irc.client["channels"].split(" "):
        irc.send("JOIN", channel)

@saxo.event("PING")
def ping(irc):
    irc.send("PONG", irc.client["nick"])
