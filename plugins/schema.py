# http://inamidst.com/saxo/
# Created by Sean B. Palmer

import saxo

@saxo.setup
def instances(irc):
    if not "saxo_instances" in irc.db:
        irc.db["saxo_instances"].create(
            ("pid", int))

@saxo.setup
def periodic(irc):
    sqlite3_schema = [(0, 'name', 'TEXT', 0, None, 1),
                      (1, 'period', 'INTEGER', 0, None, 0),
                      (2, 'recent', 'INTEGER', 0, None, 0),
                      (3, 'command', 'BLOB', 0, None, 0),
                      (4, 'args', 'BLOB', 0, None, 0)]

    if "saxo_periodic" in irc.db:
        schema = list(irc.db["saxo_periodic"].schema())
        if schema != sqlite3_schema:
            del irc.db["saxo_periodic"]

    if "saxo_periodic" not in irc.db:
        irc.db["saxo_periodic"].create(("name", "TEXT PRIMARY KEY"),
                                       ("period", int),
                                       ("recent", int),
                                       ("command", bytes),
                                       ("args", bytes))

@saxo.setup
def schedule(irc):
    if not "saxo_schedule" in irc.db:
        irc.db["saxo_schedule"].create(
            ("unixtime", int),
            ("command", bytes),
            ("args", bytes))
