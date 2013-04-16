# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import os
import queue
import socket
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

def send(base):
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client_sock = os.path.join(base, "client.sock")
    client.connect(client_sock)

    while True:
        octets = outgoing.get()
        print("SEND:", octets)
        client.send(octets + b"\n")

def start(base):
    generic.exit_cleanly()

    database_filename = os.path.join(base, "database.sqlite3")
    with database.Database(database_filename) as db:
        if not "saxo_periodic" in db:
            db["saxo_periodic"].create(
                ("period", int),
                ("command", bytes),
                ("args", bytes))

            # TODO: Or "check_connection"
            db["saxo_periodic"].insert(
                (180, b"ping", b""))

        if not "saxo_schedule" in db:
            db["saxo_schedule"].create(
                ("unixtime", int),
                ("command", bytes),
                ("args", bytes))

        generic.thread(send, base)

        sockname =  os.path.join(base, "scheduler.sock")
        generic.serve(sockname, incoming)

        generic.instruction(outgoing, "message", "started scheduler")

        periodic = {}
        current = time.time()
        for period, command, args in db["saxo_periodic"]:
            periodic[(period, command, args)] = current + period

        def tick():
            start = time.time()

            for (period, command, args), when in periodic.items():
                if when < start:
                    outgoing.put(command + b" " + args)
                    periodic[(period, command, args)] += period

            elapsed = time.time() - start
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)

            return True

        def tock():
            ...

        while tick():
            tock()

        # while True:
        #     input = incoming.get()
        #     print(repr(input))
