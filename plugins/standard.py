# http://inamidst.com/saxo/
# Created by Sean B. Palmer

import saxo

@saxo.event("PRIVMSG")
def exclamation(irc):
    if irc.text == irc.config["nick"] + "!":
        irc.say(irc.nick + "!")

# TODO: Move this into prefix.py?
@saxo.event("PRIVMSG")
def prefix(irc):
    if irc.text == irc.config["nick"] + ": prefix?":
        irc.reply('"' + irc.config["prefix"] + '"')
