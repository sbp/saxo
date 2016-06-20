# http://inamidst.com/saxo/
# Created by Sean B. Palmer

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
        else:
            # Drop messages more than a year old
            now = int(time.time())
            one_year = 60 * 60 * 24 * 366
            query = "SELECT * FROM saxo_to"
            for row in db.query(query):
                date_posted = row[:3]
                if now - date_posted > one_year:
                    del db["saxo_to"][row]

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
