# Copyright 2013-4, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import saxo

@saxo.command("join", owner=True)
def join(irc):
    if irc.arg.startswith("#"):
        irc.client("join", irc.arg)
        irc.say("Joining %s" % irc.arg)

@saxo.command("leave", owner=True)
def leave(irc):
    if irc.arg.startswith("#"):
        irc.send("PART", irc.arg)
        irc.say("Leaving %s" % irc.arg)

@saxo.command("part", owner=True)
def part(irc):
    if irc.arg.startswith("#"):
        irc.client("part", irc.arg)
        irc.say("Parting %s" % irc.arg)

@saxo.command("prefix", owner=True)
def prefix(irc):
    irc.client("prefix", irc.arg)
    irc.say("Setting prefix to %r" % irc.arg)

@saxo.command("quit", owner=True)
def quit(irc):
    irc.client("quit")

@saxo.command("reload", owner=True)
def reload(irc):
    irc.client("reload", irc.sender)

@saxo.command("visit", owner=True)
def visit(irc):
    if irc.arg.startswith("#"):
        irc.send("JOIN", irc.arg)
        irc.say("Visiting %s" % irc.arg)
