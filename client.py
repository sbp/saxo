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
    from . import generic
    from .saxo import path as saxo_path
else:
    import generic
    from saxo import path as saxo_path

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
        self.commands = {}

    def run(self):
        self.load()
        self.connect()
        self.handle()

    def load(self):
        # Load events
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

        # Load commands
        commands = os.path.join(self.base, "commands")
        if os.path.isdir(commands):
            self.commands.clear()
            for name in os.listdir(commands):
                print("Loaded command:", name)
                self.commands[name] = os.path.join(commands, name)

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

                if command == "PRIVMSG":
                    privmsg = parameters[1]
                    if privmsg.startswith("."):
                        if " " in privmsg:
                            cmd, arg = privmsg[1:].split(" ", 1)
                        else:
                            cmd, arg = privmsg[1:], ""

                        if cmd in self.commands:
                            self.command(parameters[0], cmd, arg)

                if command in self.events:
                    for function in self.events[command]:
                        function(self, prefix, parameters)

            else:
                print("?", input[0])

    def command(self, sender, cmd, arg):
        path = self.commands[cmd]

        def process(path, arg):
            env = os.environ.copy()
            env["PYTHONPATH"] = saxo_path

            proc = subprocess.Popen([path], env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            octets = (arg + "\n").encode("utf-8", "replace")

            try: outs, errs = proc.communicate(octets, timeout=6)
            except subprocess.TimeoutExpired:
                proc.kill()
                outs = "Sorry, .%s took too long" % cmd
            else:
                outs = outs.decode("utf-8", "replace")
            if not outs:
                outs = "Sorry, .%s did not respond" % cmd

            self.send("PRIVMSG", sender, outs)
        generic.thread(process, path, arg)

    def send(self, *args):
        if len(args) > 1:
            args = args[:-1] + (":" + args[-1],)
        text = re.sub(r"[\r\n]", "", " ".join(args))
        outgoing.put(text.encode("utf-8", "replace")[:510] + b"\r\n")

E_NO_PLUGINS = """
The plugins directory is necessary for saxo to work. If it was deleted
accidentally, just make a new empty directory and saxo will automatically
populate it with the core plugin that it needs to work.
"""

def start(base):
    # Save PEP 3122!
    if "." in __name__:
        from . import core
    else:
        import core

    generic.exit_cleanly()

    plugins = os.path.join(base, "plugins")
    if not os.path.isdir(plugins):
        generic.error("no plugins directory: `%s`" % plugins, E_NO_PLUGINS)

    # Could check core.version
    core_plugin = os.path.join(base, "plugins", "core.py")
    if os.path.getmtime(core.__file__) > os.path.getmtime(core_plugin):
        shutil.copy2(core.__file__, core_plugin)

    opt = configparser.ConfigParser()
    config = os.path.join(base, "config")
    opt.read(config)

    scripts = os.path.dirname(sys.modules["__main__"].__file__)
    scripts = os.path.abspath(scripts)

    sockname =  os.path.join(base, "client.sock")
    generic.serve(sockname, incoming)

    # start_scheduler
    saxo_scheduler = os.path.join(scripts, "saxo-scheduler")
    subprocess.Popen([saxo_scheduler, base])

    saxo = Saxo(base, opt)
    saxo.run()
