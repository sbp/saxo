# http://inamidst.com/saxo/
# Created by Sean B. Palmer

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

class Scheduler(object):
    def __init__(self, client):
        self.client = client
        self.duration = 0.5
        self.connections = 0
        self.connected = False
        self.running = False

    def message(self, msg):
        self.client.put(("message", "Scheduler: %s" % msg))

    # TODO: Make a monotonic version of time.time()
    def tick(self):
        start = time.time()
        # Check for new scheduled commands
        # TODO: New periodic commands
        while True:
            try: a, b = incoming.get(timeout=self.duration / 6)
            except queue.Empty:
                break
            else:
                if a == "connected":
                    self.connections += 1
                    self.message("connected (%s)" % self.connections)
                    self.connected = True
                elif a == "disconnected":
                    self.message("disconnected, and stopped")
                    self.connected = False
                    self.running = False
                elif a == "start":
                    if self.connected:
                        self.message("started at tick %s" % start)
                        self.running = True
                elif a == "stop":
                    self.message("stopped")
                    self.running = False
                elif a == "schedule.add":
                    if "saxo_schedule" in self.db:
                        self.db["saxo_schedule"].insert(b)
                else:
                    self.message("unknown instruction: %s" % a)

                elapsed = time.time() - start
                if elapsed > (self.duration / 3):
                    break

        if self.connected and self.running:
            # Periodic commands
            if "saxo_periodic" in self.db:
                deletions = []
                additions = []
                periodic = self.db["saxo_periodic"].rows(order="recent")
                for (name, period, recent, command, args) in periodic:
                    # find next %0 point after start
                    unixtime = recent - (recent % period) + period
                    if unixtime > int(start):
                        continue
                    cmd = command.decode("ascii")
                    self.client.put((cmd,) + common.b64unpickle(args))
                    deletions.append((name, period, recent, command, args))
                    additions.append((name, period, int(start), command, args))

                for deletion in deletions:
                    del self.db["saxo_periodic"][deletion]
                for addition in additions:
                    self.db["saxo_periodic"].insert(addition)

            # Scheduled commands
            if "saxo_schedule" in self.db:
                deletions[:] = []
                schedule = self.db["saxo_schedule"].rows(order="unixtime")
                for (unixtime, command, args) in schedule:
                    if unixtime > start:
                        break
                    cmd = command.decode("ascii")
                    self.client.put((cmd,) + common.b64unpickle(args))
                    deletions.append((unixtime, command, args))

                for deletion in deletions:
                    del self.db["saxo_schedule"][deletion]

        elapsed = time.time() - start
        if elapsed < self.duration:
            time.sleep(self.duration - elapsed)

        return True

    def tock(self):
        ...

    def start(self, base):
        database_filename = os.path.join(base, "database.sqlite3")
        with sqlite.Database(database_filename) as self.db:
            self.message("initialised, waiting for instructions")
            while self.tick():
                self.tock()
