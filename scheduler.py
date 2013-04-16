# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import os
import queue
import socket

# Save PEP 3122!
if "." in __name__:
    from . import generic
else:
    import generic

incoming = queue.Queue()
outgoing = queue.Queue()

def send(base):
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client_sock = os.path.join(base, "client.sock")
    client.connect(client_sock)

    while True:
        octets = outgoing.get()
        client.send(octets + b"\n")

def start(base):
    generic.exit_cleanly()

    generic.thread(send, base)
    sockname =  os.path.join(base, "scheduler.sock")
    generic.serve(sockname, incoming)

    outgoing.put(b"started scheduler")
    while True:
        input = incoming.get()
        print(repr(input))

    # saxo_periodic
    # saxo_schedule

    # the reminder structure could be generic
    # so, e.g. you could set a reload. just allow anything in the IPC protocol
    # use a heap to cache upcoming reminders

    # saxo_periodic
    # period (int), command (text? blob?), args (pickled blob)

    # saxo_schedule
    # unixtime (int), command (text? blob?), args (pickled blob)
