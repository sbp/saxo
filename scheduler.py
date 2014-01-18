# Copyright 2013-4, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import os
import queue
import socket
import sys
import time

# Save PEP 3122!
if "." in __name__:
    from . import sqlite
    from . import common
else:
    import sqlite
    import common

incoming = queue.Queue()

def start(base, client):
    database_filename = os.path.join(base, "database.sqlite3")
    with sqlite.Database(database_filename) as db:
        if not "saxo_instances" in db:
            db["saxo_instances"].create(
                ("pid", int))

        # Remove any values from previous instances
        for row in db["saxo_instances"]:
            del db["saxo_instances"][row]
        # Add our value
        db["saxo_instances"].insert((os.getpid(),))

        if not "saxo_periodic" in db:
            db["saxo_periodic"].create(
                ("period", int),
                ("command", bytes),
                ("args", bytes))
        else:
            for row in db["saxo_periodic"]:
                del db["saxo_periodic"][row]

        # TODO: Or "check_connection" instead of "ping"
        db["saxo_periodic"].insert((180, b"ping", b""))
        db["saxo_periodic"].insert((25, b"instances", b""))

        if not "saxo_schedule" in db:
            db["saxo_schedule"].create(
                ("unixtime", int),
                ("command", bytes),
                ("args", bytes))

        client.put(("message", "started scheduler"))

        periodic = {}
        current = time.time()
        for period, command, args in db["saxo_periodic"]:
            periodic[(period, command, args)] = current + period

        duration = 1/2

        def tick():
            start = time.time()

            # Check for new scheduled commands
            # TODO: New periodic commands
            while True:
                try: triple = incoming.get(timeout=1/6 * duration)
                except queue.Empty:
                    break
                else:
                    db["saxo_schedule"].insert(triple)
                    elapsed = time.time() - start
                    if elapsed > (1/3 * duration):
                        break

            # Periodic commands
            for (period, command, args), when in periodic.items():
                if when < start:
                    # Calling this command causes the following del to fail
                    cmd = command.decode("ascii")
                    client.put((cmd,) + common.b64unpickle(args))
                    periodic[(period, command, args)] += period

            # Scheduled commands
            schedule = db["saxo_schedule"].rows(order="unixtime")
            for (unixtime, command, args) in schedule:
                if unixtime > start:
                    break
                # Calling this command causes the following del to fail
                cmd = command.decode("ascii")
                client.put((cmd,) + common.b64unpickle(args))
                del db["saxo_schedule"][(unixtime, command, args)]

            elapsed = time.time() - start
            if elapsed < duration:
                time.sleep(duration - elapsed)

            return True

        def tock():
            ...

        while tick():
            tock()
