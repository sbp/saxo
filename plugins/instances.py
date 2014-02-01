# http://inamidst.com/saxo/
# Created by Sean B. Palmer

import os
import saxo

def dependencies(*deps):
    def decorator(function):
        function.saxo_deps = deps
        return function
    return decorator

@saxo.setup
@dependencies("schema.instances")
def populate(irc):
    # Remove any values from previous instances
    for row in irc.db["saxo_instances"]:
        del irc.db["saxo_instances"][row]

    # Add our value
    irc.db["saxo_instances"].insert((os.getpid(),))
