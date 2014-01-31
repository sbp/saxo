# http://inamidst.com/saxo/
# Created by Sean B. Palmer

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
