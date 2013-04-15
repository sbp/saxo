# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

from saxo import event

@event("PING")
def ping(saxo, prefix, parameters):
    saxo.send("PONG", saxo.opt["client"]["nick"])

@event("PRIVMSG")
def exclamation(saxo, prefix, parameters):
    # ('nick', '~user', 'host') ['#channel', 'text']
    nick, user, host = prefix
    channel, text = tuple(parameters)

    if text == saxo.opt["client"]["nick"] + "!":
        saxo.send("PRIVMSG", channel, nick + "!")

@event(":1st")
def connected(saxo, prefix, parameters):
    saxo.send("NICK", saxo.opt["client"]["nick"])
    saxo.send("USER", saxo.opt["client"]["nick"], "+iw", saxo.opt["client"]["nick"], "saxo")
    for channel in saxo.opt["client"]["channels"].split(" "):
        saxo.send("JOIN", channel)
