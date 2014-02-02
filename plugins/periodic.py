# http://inamidst.com/saxo/
# Created by Sean B. Palmer

import time
import saxo

def dependencies(*deps):
    def decorator(function):
        function.saxo_deps = deps
        return function
    return decorator

def replace(irc, *args):
    irc.db["saxo_periodic"].replace(args)

@saxo.setup
@dependencies("schema.periodic")
def populate(irc):
    # Periodic tasks whose names start with "@" are temporary
    # This code deletes those tasks on initialisation
    temporary = []
    for row in irc.db["saxo_periodic"].rows():
        if row[0].startswith("@"):
            temporary.append(row)
    for row in temporary:
        del irc.db["saxo_periodic"][row]

    current = int(time.time())
    # TODO: Or "check_connection" instead of "ping"
    replace(irc, "check connection", 180, current, b"ping", b"")
    replace(irc, "check unique", 20, current, b"instances", b"")
