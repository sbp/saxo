# Copyright 2013-4, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import saxo

@saxo.event(":connected")
def connected(irc):
    if "password" in irc.config["server"]:
        irc.send("PASS", irc.config["server"]["password"])

@saxo.event(":1st")
def first(irc):
    irc.send("NICK", irc.config["nick"])
    irc.send("USER", irc.config["nick"], "+iw", irc.config["nick"], "saxo")
    for channel in irc.config["channels"].split(" "):
        irc.send("JOIN", channel)
    irc.send("WHO", irc.config["nick"])

@saxo.event("352")
def who(irc):
    if irc.parameters[0] == irc.config["nick"]:
        nick = irc.parameters[0]
        user = irc.parameters[2]
        host = irc.parameters[3]
        irc.client("address", nick + "!" + user + "@" + host)

@saxo.event("PING")
def ping(irc):
    irc.send("PONG", irc.config["nick"])
