# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import saxo

@saxo.event("PRIVMSG")
def exclamation(irc):
    if irc.text == irc.client["nick"] + "!":
        irc.say(irc.nick + "!")

@saxo.event("PRIVMSG")
def prefix(irc):
    if irc.text == irc.client["nick"] + ": prefix?":
        irc.reply('"' + irc.client["prefix"] + '"')

@saxo.command("reload")
def reload(irc):
    if "owner" in irc.client:
        if irc.prefix == irc.client["owner"]:
            irc.queue(("reload", irc.sender))
