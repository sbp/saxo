# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import saxo

def owner(irc):
    if "owner" in irc.config:
        if irc.prefix == irc.config["owner"]:
            return True
        if irc.identified:
            owner_nick = irc.config["owner"].split("!", 1)[0]
            if irc.nick == owner_nick:
                return True
    return False

@saxo.command("join")
def join(irc):
    if owner(irc):
        if irc.arg.startswith("#"):
            irc.client("join", irc.arg)
            irc.say("Joining %s" % irc.arg)

@saxo.command("leave")
def leave(irc):
    if owner(irc):
        if irc.arg.startswith("#"):
            irc.send("PART", irc.arg)
            irc.say("Leaving %s" % irc.arg)

@saxo.command("part")
def part(irc):
    if owner(irc):
        if irc.arg.startswith("#"):
            irc.client("part", irc.arg)
            irc.say("Parting %s" % irc.arg)

@saxo.command("prefix")
def prefix(irc):
    if owner(irc):
        irc.client("prefix", irc.arg)
        irc.say("Setting prefix to %r" % irc.arg)

@saxo.command("quit")
def quit(irc):
    if owner(irc):
        irc.client("quit")

@saxo.command("reload")
def reload(irc):
    if owner(irc):
        irc.client("reload", irc.sender)

@saxo.command("visit")
def visit(irc):
    if owner(irc):
        if irc.arg.startswith("#"):
            irc.send("JOIN", irc.arg)
            irc.say("Visiting %s" % irc.arg)
