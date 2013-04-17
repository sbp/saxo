# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import saxo

@saxo.event(":1st")
def connected(irc):
    irc.send("NICK", irc.client["nick"])
    irc.send("USER", irc.client["nick"], "+iw", irc.client["nick"], "saxo")
    for channel in irc.client["channels"].split(" "):
        irc.send("JOIN", channel)
    irc.send("WHO", irc.client["nick"])

@saxo.event("352")
def who(irc):
    if irc.parameters[0] == irc.client["nick"]:
        nick = irc.parameters[0]
        user = irc.parameters[2]
        host = irc.parameters[3]
        irc.queue(("address", nick + "!" + user + "@" + host))

@saxo.event("PING")
def ping(irc):
    irc.send("PONG", irc.client["nick"])
