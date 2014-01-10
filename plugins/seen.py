# Copyright 2012-4, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import os.path
import saxo
import time

@saxo.setup
def setup(irc):
    path = os.path.join(irc.base, "database.sqlite3")
    with saxo.database(path) as db:
        if "saxo_seen" not in db:
            db["saxo_seen"].create(
                ("nick", "TEXT PRIMARY KEY"),
                ("unixtime", int),
                ("channel", str))
        # TODO: Drop nicknames seen more than a year ago

        if "saxo_private" not in db:
            db["saxo_private"].create(
                ("channel", "TEXT PRIMARY KEY"))

@saxo.event("PRIVMSG")
def record(irc):
    if irc.sender.startswith("#"):
        path = os.path.join(irc.base, "database.sqlite3")
        with saxo.database(path) as db:
            if "saxo_seen" in db:
                # TODO: db["saxo_seen"].replace
                command = "INSERT OR REPLACE INTO saxo_seen" + \
                    " (nick,unixtime,channel) VALUES(?,?,?)"
                db.execute(command, irc.nick, int(time.time()), irc.sender)
                db.commit()

@saxo.command("seen")
def seen(irc):
    path = os.path.join(irc.base, "database.sqlite3")
    with saxo.database(path) as db:
        if "saxo_seen" in db:
            query = "SELECT * FROM saxo_seen WHERE nick = ?"
            for (nick, unixtime, channel) in db.query(query, irc.arg):
                private = False
                query = "SELECT * FROM saxo_private WHERE channel = ?"
                for row in db.query(query, channel):
                    if row[0] == channel:
                        private = True
                        break
                if not private:
                    formatted = time.ctime(unixtime)
                    irc.say("%s was on %s at %s" % (nick, channel, formatted))
                else:
                    irc.say("Sorry, there is no available data")
                break
        else:
            irc.say("Sorry, there is no saxo_seen database table")

@saxo.command("private-channel")
def private_channel(irc):
    if "owner" in irc.config:
        if irc.prefix == irc.config["owner"]:
            path = os.path.join(irc.base, "database.sqlite3")
            with saxo.database(path) as db:
                if "saxo_private" in db:
                    command = "INSERT OR REPLACE INTO saxo_private" + \
                        " (channel) VALUES(?)"
                    db.execute(command, irc.arg)
                    db.commit()
                    irc.say("Set %s as private" % irc.arg)

@saxo.command("public-channel")
def public_channel(irc):
    if "owner" in irc.config:
        if irc.prefix == irc.config["owner"]:
            path = os.path.join(irc.base, "database.sqlite3")
            with saxo.database(path) as db:
                if "saxo_private" in db:
                    deleted = False
                    query = "SELECT * FROM saxo_private WHERE channel = ?"
                    for row in db.query(query, irc.arg):
                       del db["saxo_private"][row]
                       deleted = True
                    if deleted:
                       irc.say("Set %s as public" % irc.arg)
                    else:
                       irc.say("Already set as public")
