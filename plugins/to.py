# Copyright 2012-4, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import os.path
import saxo

@saxo.setup
def setup(irc):
    path = os.path.join(irc.base, "database.sqlite3")
    with saxo.database(path) as db:
        if "saxo_to" not in db:
            db["saxo_to"].create(
                ("sender", str),
                ("recipient", str),
                ("unixtime", int),
                ("channel", str),
                ("message", str))
        # TODO: Drop messages more than a year old

@saxo.event("PRIVMSG")
def deliver(irc):
    path = os.path.join(irc.base, "database.sqlite3")
    with saxo.database(path) as db:
        query = "SELECT * FROM saxo_to WHERE recipient = ?"
        for row in db.query(query, irc.nick):
            print(row)
            recipient = row[1]
            sender = row[0]
            message = row[4]
            irc.say("%s: <%s> %s" % (recipient, sender, message))
            del db["saxo_to"][row]
