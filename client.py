# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import atexit
import configparser
import imp
import importlib
import os.path
import queue
import re
import shutil
import socket
import subprocess
import sys
import threading
import time

# Save PEP 3122!
if "." in __name__:
    from . import generic
    from .saxo import path as saxo_path
else:
    import generic
    from saxo import path as saxo_path

# TODO: Make printing thread-safe

incoming = queue.Queue()
outgoing = queue.Queue()

regex_optional_prefix = re.compile(r"(?::([^! ]*)!?([^@ ]*)@?([^ ]*))?")
regex_parameter = re.compile(r"((?:(?<= :)[^\r\n]*)|(?:[^: \r\n][^ \r\n]*))")

def parse(octets):
    text = octets.decode("utf-8", "replace")

    match_prefix = regex_optional_prefix.match(text)
    params = regex_parameter.findall(text[match_prefix.end():])
    return match_prefix.groups(), params[0], params[1:]

class ThreadSafeEnvironment(object):
    def __init__(self, saxo, prefix, command, parameters):
        self.nick = prefix[0]
        self.user = prefix[1]
        self.host = prefix[2]

        if self.nick and self.user and self.host:
            self.prefix = self.nick + "!" + self.user + "@" + self.host

        self.command = command
        self.parameters = parameters

        for key in saxo.opt:
            setattr(self, key, dict(saxo.opt[key]))

        if command == "PRIVMSG":
            self.sender = self.parameters[0]
            self.text = self.parameters[1]
            self.private = self.sender == self.client["nick"]
            if saxo.address:
                # TODO: Why was this 498 for duxlot?
                self.limit = 493 - len(self.sender + saxo.address)

        def send(*args):
            saxo.send(*args)
        self.send = send

        if hasattr(self, "sender"):
            # @staticmethod
            def say(text):
                saxo.send("PRIVMSG", self.sender, text)
            self.say = say

        if hasattr(self, "nick") and hasattr(self, "sender"):
            # @staticmethod
            def reply(text):
                saxo.send("PRIVMSG", self.sender, self.nick + ": " + text)
            self.reply = reply

    def queue(self, item):
        incoming.put(item)

# threaded
def socket_receive(sock):
    with sock.makefile("rb") as s:
        # TODO: How do we know when we're connected?
        incoming.put(("receive_conn",))
        for octets in s:
            incoming.put(("remote", octets))
    incoming.put(("receive_disco",))

# threaded
def socket_send(sock):
    def sending(sock):
        with sock.makefile("wb") as s:
            incoming.put(("send_conn",))
            while True:
                octets = outgoing.get()
                if octets == None:
                    break

                print("->", repr(octets.decode("ascii")))
                s.write(octets)
                s.flush()

    try: sending(sock)
    except BrokenPipeError:
        ...
    incoming.put(("send_disco",))

class Saxo(object):
    def __init__(self, base, opt):
        self.base = base
        self.opt = opt
        self.events = {}
        self.commands = {}
        self.address = None
        self.discotimer = None
        self.receiving = False
        self.sending = False

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
            if not name in sys.modules:
                try: module = importlib.import_module(name)
                except Exception as err:
                    print("Error loading %s:" % name, err)
            else:
                module = sys.modules[name]
                module = imp.reload(module)

            for attr in dir(module):
                obj = getattr(module, attr)

                if hasattr(obj, "saxo_event"):
                    try: self.events[obj.saxo_event].append(obj)
                    except KeyError:
                        self.events[obj.saxo_event] = [obj]

                elif hasattr(obj, "saxo_setup"):
                    obj(self)

            # print("Loaded module:", name)

        sys.path[:1] = []

        # Load commands
        commands = os.path.join(self.base, "commands")
        if os.path.isdir(commands):
            self.commands.clear()
            for name in os.listdir(commands):
                # print("Loaded command:", name)
                self.commands[name] = os.path.join(commands, name)

    def connect(self):
        host = self.opt["server"]["host"]
        port = int(self.opt["server"]["port"])

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("Connecting to %s:%s" % (host, port))
        self.sock.connect((host, port))
        self.first = True

        generic.thread(socket_receive, self.sock)
        generic.thread(socket_send, self.sock)

    def handle(self):
        while True:
            instruction_args = incoming.get()
            instruction = instruction_args[0]
            args = tuple(instruction_args[1:])

            if instruction != "remote":
                print("handle:", instruction, args)

            if hasattr(self, "instruction_" + instruction):
                method = getattr(self, "instruction_" + instruction)
                try: method(*args)
                except Exception as err:
                    print("handle error:", err)
            else:
                print("Unknown instruction:", instruction)

    def instruction_address(self, address):
        self.address = address

    def instruction_connected(self):
        if ":connected" in self.events:
            for function in self.events[":connected"]:
                function(self, None, None)

    def instruction_message(self, text):
        print("IPC message:", text)

    def instruction_msg(self, destination, text):
        self.send("PRIVMSG", destination, text)

    def instruction_ping(self):
        self.send("PING", self.opt["client"]["nick"])

        def reconnect():
            incoming.put(("reconnect",))
        self.discotimer = threading.Timer(30, reconnect)
        self.discotimer.start()

    def instruction_quit(self):
        # Never call this from a thread, otherwise the following can give an OSError
        self.send("QUIT")
        outgoing.put(None) # Closes the send thread
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        sys.exit()

    def instruction_receive_conn(self):
        self.receiving = True

    def instruction_receive_disco(self):
        self.receiving = False

    def instruction_reconnect(self):
        # Never call this from a thread, otherwise the following can give an OSError
        outgoing.put(None) # Closes the send thread
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()

        time.sleep(3)
        for attempt in range(7):
            if self.receiving or self.sending:
                time.sleep(1)
            # TODO: If the threads are still active, they should be killed
            # Unfortunately, threads in python can't be killed

        self.connect()

    def instruction_reload(self, destination=None):
        before = time.time()
        self.load()
        elapsed = time.time() - before
        if destination:
            self.send("PRIVMSG", destination,
                "Reloaded in %s seconds" % round(elapsed, 3))

    def instruction_remote(self, octets):
        print(repr(octets))
        prefix, command, parameters = parse(octets)

        if command == "PRIVMSG":
            privmsg = parameters[1]
            pfx = self.opt["client"]["prefix"]
            length = len(pfx)

            if privmsg.startswith(pfx):
                privmsg = privmsg[length:]
                if " " in privmsg:
                    cmd, arg = privmsg.split(" ", 1)
                else:
                    cmd, arg = privmsg, ""

                if cmd in self.commands:
                    self.command(parameters[0], cmd, arg)

        elif command == "PONG":
            if self.discotimer is not None:
                try:
                    self.discotimer.cancel()
                    self.discotimer = None
                    print("Cancelled the disco timer")
                except:
                    ...

        irc = ThreadSafeEnvironment(self, prefix, command, parameters)
        def safe(function, irc):
            try: function(irc)
            except Exception as err:
                print(err)

        # TODO: Remove duplication below
        if self.first is True:
            if ":1st" in self.events:
                for function in self.events[":1st"]:
                    if not function.saxo_synchronous:
                        generic.thread(safe, function, irc)
                    else:
                        safe(function, irc)
            self.first = False

        if command in self.events:
            for function in self.events[command]:
                if not function.saxo_synchronous:
                    generic.thread(safe, function, irc)
                else:
                    safe(function, irc)

    def instruction_schedule(self, unixtime, command, args):
        unixtime = str(unixtime).encode("ascii")
        command = command.encode("ascii")
        args = generic.b64pickle(args)

        octets = unixtime + b" " + command + b" " + args
        scheduler_process.stdin.write(octets + b"\n")

    def instruction_send(self, *args):
        self.send(*args)

    def instruction_send_conn(self):
        self.sending = True

    def instruction_send_disco(self):
        self.sending = False

    def command(self, sender, cmd, arg):
        path = self.commands[cmd]

        def process(path, arg):
            env = os.environ.copy()
            env["PYTHONPATH"] = saxo_path

            octets = arg.encode("utf-8", "replace")
            proc = subprocess.Popen([path, octets, self.base], env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)

            try: outs, errs = proc.communicate(timeout=6)
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
    global scheduler_process
    generic.exit_cleanly()

    plugins = os.path.join(base, "plugins")
    if not os.path.isdir(plugins):
        generic.error("no plugins directory: `%s`" % plugins, E_NO_PLUGINS)

    generic.populate(saxo_path, base)

    opt = configparser.ConfigParser()
    config = os.path.join(base, "config")
    opt.read(config)
    # TODO: defaulting?

    scripts = os.path.dirname(sys.modules["__main__"].__file__)
    scripts = os.path.abspath(scripts)

    sockname =  os.path.join(base, "client.sock")
    # TODO: Not generic anymore; isn't used in scheduler
    generic.serve(sockname, incoming)
    os.chmod(sockname, 0o600)
    def remove_sock(sockname):
        os.remove(sockname)
    atexit.register(remove_sock, sockname)

    # start_scheduler
    saxo_scheduler = os.path.join(scripts, "saxo-scheduler")
    scheduler_process = subprocess.Popen([saxo_scheduler, base],
        stdin=subprocess.PIPE)

    def quit_scheduler(scheduler_process):
        scheduler_process.kill()
    atexit.register(quit_scheduler, scheduler_process)

    saxo = Saxo(base, opt)
    saxo.run()
