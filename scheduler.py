# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import os
import queue
import socket
import sys
import time

# Save PEP 3122!
if "." in __name__:
    from . import database
    from . import generic
else:
    import database
    import generic

incoming = queue.Queue()
outgoing = queue.Queue()

# threaded
def receive():
    for line in sys.stdin.buffer:
        try:
            octets = line[:-1] # Up to b"\n"
            unixtime, command, args = octets.split(b" ", 2)
            unixtime = int(unixtime)
            incoming.put((unixtime, command, args))
        except Exception as err:
            print("Schedule Parse Error:", err)
            continue

# threaded
def send(base):
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client_sock = os.path.join(base, "client.sock")
    client.connect(client_sock)

    while True:
        octets = outgoing.get()
        print("SEND:", octets)
        client.send(octets + b"\n")

def start(base, client=None):
    process = client is None
    if process:
        generic.exit_cleanly()

    database_filename = os.path.join(base, "database.sqlite3")
    with database.Database(database_filename) as db:
        if not "saxo_periodic" in db:
            db["saxo_periodic"].create(
                ("period", int),
                ("command", bytes),
                ("args", bytes))

            # TODO: Or "check_connection"
            db["saxo_periodic"].insert((180, b"ping", b""))

        if not "saxo_schedule" in db:
            db["saxo_schedule"].create(
                ("unixtime", int),
                ("command", bytes),
                ("args", bytes))

        if process:
            generic.thread(receive)
            generic.thread(send, base)

        if process:
            generic.instruction(outgoing, "message", "started scheduler")
        else:
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
                    print("Scheduling:", triple) # TODO: Remove, debug
                    db["saxo_schedule"].insert(triple)
                    elapsed = time.time() - start
                    if elapsed > (1/3 * duration):
                        break

            # Periodic commands
            for (period, command, args), when in periodic.items():
                if when < start:
                    if process:
                        outgoing.put(command + b" " + args)
                    else:
                        # Calling this command causes the following del to fail
                        cmd = command.decode("ascii")
                        client.put((cmd,) + generic.b64unpickle(args))
                    periodic[(period, command, args)] += period

            # Scheduled commands
            schedule = db["saxo_schedule"].rows(order="unixtime")
            for (unixtime, command, args) in schedule:
                if unixtime > start:
                    break
                if process:
                    outgoing.put(command + b" " + args)
                else:
                    # Calling this command causes the following del to fail
                    cmd = command.decode("ascii")
                    client.put((cmd,) + generic.b64unpickle(args))
                del db["saxo_schedule"][(unixtime, command, args)]

            elapsed = time.time() - start
            if elapsed < duration:
                time.sleep(duration - elapsed)

            return True

        def tock():
            ...

        while tick():
            tock()
