# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import configparser
import importlib
import os.path
import queue
import re
import shutil
import socket
import subprocess
import sys

# Save PEP 3122!
if "." in __name__:
    from . import core
    from . import generic
else:
    import core
    import generic

incoming = queue.Queue()
outgoing = queue.Queue()

regex_optional_prefix = re.compile(r"(?::([^! ]*)!?([^@ ]*)@?([^ ]*))?")
regex_parameter = re.compile(r"((?:(?<= :)[^\r\n]*)|(?:[^: \r\n][^ \r\n]*))")

def parse(octets):
    text = octets.decode("utf-8", "replace")

    match_prefix = regex_optional_prefix.match(text)
    params = regex_parameter.findall(text[match_prefix.end():])
    return match_prefix.groups(), params[0], params[1:]

# threaded
def socket_receive(sock):
    with sock.makefile("rb") as s:
        # TODO: How do we know when we're connected?
        incoming.put(("connected",))

        for octets in s:
            incoming.put(("remote", octets))
    incoming.put(("disconnected",))

# threaded
def socket_send(sock):
    with sock.makefile("wb") as s:
        while True:
            octets = outgoing.get()
            print("->", repr(octets.decode("ascii")))
            s.write(octets)
            s.flush()
    incoming.put(("disco",))

class Saxo(object):
    def __init__(self, base, opt):
        self.base = base
        self.opt = opt

        self.events = {}

    def run(self):
        self.load()
        self.connect()
        self.handle()

    def load(self):
        self.events.clear()
        plugins = os.path.join(self.base, "plugins")
        sys.path[:0] = [plugins]

        for name in os.listdir(plugins):
            if ("_" in name) or (not name.endswith(".py")):
                continue
            name = name[:-3]
            module = importlib.import_module(name)
            for attr in dir(module):
                obj = getattr(module, attr)
                if hasattr(obj, "saxo_event"):
                    try: self.events[obj.saxo_event].append(obj)
                    except KeyError:
                        self.events[obj.saxo_event] = [obj]
            print("Loaded module:", name)

        sys.path[:1] = []

    def connect(self):
        host = self.opt["server"]["host"]
        port = int(self.opt["server"]["port"])

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("Connecting to %s:%s" % (host, port))
        sock.connect((host, port))

        generic.thread(socket_receive, sock)
        generic.thread(socket_send, sock)

    def handle(self):
        while True:
            input = incoming.get()

            if input[0] == "connected":
                if ":connected" in self.events:
                    for function in self.events[":connected"]:
                        function(self, None, None)

            elif input[0] == "local":
                print("local", repr(input[1]))

            elif input[0] == "remote":
                octets = input[1]
                print(repr(octets))
                prefix, command, parameters = parse(octets)

                if command in self.events:
                    for function in self.events[command]:
                        function(self, prefix, parameters)

            else:
                print("?", input[0])

    def send(self, *args):
        if len(args) > 1:
            args = args[:-1] + (":" + args[-1],)
        text = re.sub(r"[\r\n]", "", " ".join(args))
        outgoing.put(text.encode("utf-8", "replace")[:510] + b"\r\n")

def utf8(text):
    return text.encode("utf-8")

def start(base):
    # TODO: Check core.version
    shutil.copy2(core.__file__, os.path.join(base, "plugins", "core.py"))

    opt = configparser.ConfigParser()
    config = os.path.join(base, "config")
    opt.read(config)

    scripts = os.path.dirname(sys.modules["__main__"].__file__)
    scripts = os.path.abspath(scripts)

    sockname =  os.path.join(base, "client.sock")
    generic.serve(sockname, incoming)

    # start_scheduler
    saxo_scheduler = os.path.join(scripts, "saxo-scheduler")
    # scheduler = 
    subprocess.Popen([saxo_scheduler, base])
    # scheduler_pid = scheduler.pid

    saxo = Saxo(base, opt)
    saxo.run()
