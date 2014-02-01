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
    current = int(time.time())
    # TODO: Or "check_connection" instead of "ping"
    replace(irc, "check connection", 180, current, b"ping", b"")
    replace(irc, "check unique", 20, current, b"instances", b"")
