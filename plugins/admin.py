# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import saxo

@saxo.command("join")
def join(irc):
    if "owner" in irc.config:
        if irc.prefix == irc.config["owner"]:
            if irc.arg.startswith("#"):
                irc.client("join", irc.arg)
                irc.say("Joining %s" % irc.arg)

@saxo.command("leave")
def leave(irc):
    if "owner" in irc.config:
        if irc.prefix == irc.config["owner"]:
            if irc.arg.startswith("#"):
                irc.send("PART", irc.arg)
                irc.say("Leaving %s" % irc.arg)

@saxo.command("part")
def part(irc):
    if "owner" in irc.config:
        if irc.prefix == irc.config["owner"]:
            if irc.arg.startswith("#"):
                irc.client("part", irc.arg)
                irc.say("Parting %s" % irc.arg)

@saxo.command("prefix")
def prefix(irc):
    if "owner" in irc.config:
        if irc.prefix == irc.config["owner"]:
            irc.client("prefix", irc.arg)
            irc.say("Setting prefix to %r" % irc.arg)

@saxo.command("quit")
def quit(irc):
    if "owner" in irc.config:
        if irc.prefix == irc.config["owner"]:
            irc.client("quit")

@saxo.command("reload")
def reload(irc):
    if "owner" in irc.config:
        if irc.prefix == irc.config["owner"]:
            irc.client("reload", irc.sender)

@saxo.command("visit")
def visit(irc):
    if "owner" in irc.config:
        if irc.prefix == irc.config["owner"]:
            if irc.arg.startswith("#"):
                irc.send("JOIN", irc.arg)
                irc.say("Visiting %s" % irc.arg)
