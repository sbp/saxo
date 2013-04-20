# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import atexit
import configparser
import imp
import importlib
import os.path
import queue
import re
import signal
import socket
import subprocess
import sys
import threading
import time

# Save PEP 3122!
if "." in __name__:
    from . import generic
    from . import scheduler
    from .saxo import path as saxo_path
else:
    import generic
    import scheduler
    from saxo import path as saxo_path

lock = threading.Lock()

def debug(*args, **kargs):
    with lock:
        try:
            print(*args, **kargs)
            sys.stdout.flush()
        except BrokenPipeError:
            sys.exit()

# List of threads:
# client.receive
# client.send
# every plugin function
# every process command, as a communication wrapper
# scheduler
# serve.listen
# every serve.connection instance

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
        self.base = saxo.base

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
        incoming.put(("receiving",))
        for octets in s:
            incoming.put(("remote", octets))
    incoming.put(("disco_receiving",))

# threaded
def socket_send(sock):
    def sending(sock):
        with sock.makefile("wb") as s:
            incoming.put(("sending",))
            while True:
                octets = outgoing.get()
                if octets == None:
                    break

                debug("->", repr(octets.decode("utf-8", "replace")))
                s.write(octets)
                s.flush()

    try: sending(sock)
    except BrokenPipeError:
        ...
    incoming.put(("disco_sending",))

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
        self.user_reconnection = False
        self.links = {}

    def run(self):
        self.load()
        self.connect()
        self.handle()

    def load(self):
        # Update symlinks
        generic.populate(saxo_path, self.base)

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
                    debug("Error loading %s:" % name, err)
            else:
                module = sys.modules[name]
                try: module = imp.reload(module)
                except Exception as err:
                    debug("Error reloading %s:" % name, err)

            for attr in dir(module):
                obj = getattr(module, attr)

                if hasattr(obj, "saxo_event"):
                    try: self.events[obj.saxo_event].append(obj)
                    except KeyError:
                        self.events[obj.saxo_event] = [obj]

                elif hasattr(obj, "saxo_setup"):
                    obj(self)

            # debug("Loaded module:", name)

        sys.path[:1] = []

        # Load commands
        commands = os.path.join(self.base, "commands")
        if os.path.isdir(commands):
            self.commands.clear()
            for name in os.listdir(commands):
                # debug("Loaded command:", name)
                self.commands[name] = os.path.join(commands, name)

    def connect(self):
        host = self.opt["server"]["host"]
        port = int(self.opt["server"]["port"])

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        debug("Connecting to %s:%s" % (host, port))
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
                debug("handle:", instruction, args)

            if not isinstance(instruction, str):
                continue

            method_name = "instruction_" + instruction
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                try: method(*args)
                except Exception as err:
                    debug("handle error:", err)
            else:
                debug("Unknown instruction:", instruction)

    def instruction_address(self, address):
        self.address = address

    def instruction_connected(self):
        if ":connected" in self.events:
            for function in self.events[":connected"]:
                function(self, None, None)

    def instruction_link(self, channel, link):
        self.links[channel] = link

    def instruction_message(self, text):
        debug("IPC message:", text)

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
        os._exit(0) # sys.exit() won't work, not sure why

    def instruction_receiving(self):
        self.receiving = True

    def instruction_disco_receiving(self):
        self.receiving = False
        if not self.user_reconnection:
            if self.sending:
                outgoing.put(None)
            else:
                incoming.put(("reconnect", False))

    def instruction_reconnect(self, close=True):
        if close:
            self.user_reconnection = True
            # Never call this from a thread, otherwise the following can give an OSError
            outgoing.put(None) # Closes the send thread
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()

        if not self.opt["client"]["flood"]:
            time.sleep(3)
        for attempt in range(7):
            if not self.opt["client"]["flood"]:
                if self.receiving or self.sending:
                    time.sleep(1)
                # TODO: If the threads are still active, they should be killed
                # Unfortunately, threads in python can't be killed

        if close:
            self.user_reconnection = False
        self.connect()

    def instruction_reload(self, destination=None):
        before = time.time()
        self.load()
        elapsed = time.time() - before
        if destination:
            self.send("PRIVMSG", destination,
                "Reloaded in %s seconds" % round(elapsed, 3))

    def instruction_remote(self, octets):
        debug(repr(octets))
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
                    self.command(prefix, parameters[0], cmd, arg)

        elif command == "PONG":
            if self.discotimer is not None:
                try:
                    self.discotimer.cancel()
                    self.discotimer = None
                    debug("Cancelled the disco timer")
                except:
                    ...

        irc = ThreadSafeEnvironment(self, prefix, command, parameters)
        def safe(function, irc):
            try: function(irc)
            except Exception as err:
                debug(err)

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
        command = command.encode("ascii")
        args = generic.b64pickle(args)
        scheduler.incoming.put((unixtime, command, args))

    def instruction_send(self, *args):
        self.send(*args)

    def instruction_sending(self):
        self.sending = True

    def instruction_disco_sending(self):
        self.sending = False
        if not self.user_reconnection:
            if not self.receiving:
                incoming.put(("reconnect", False))
            else:
                # TODO: Close the socket?
                ...

    def command(self, prefix, sender, cmd, arg):
        path = self.commands[cmd]

        def process(path, arg):
            ### TODO: Cache this
            env = os.environ.copy()
            env["PYTHONPATH"] = saxo_path
            env["SAXO_BASE"] = self.base
            env["SAXO_COMMANDS"] = os.path.join(self.base, "commands")
            ###
            env["SAXO_NICK"] = prefix[0]
            env["SAXO_SENDER"] = sender
            env["SAXO_BOT"] = self.opt["client"]["nick"]
            if sender in self.links:
                env["SAXO_URL"] = self.links[sender]

            octets = arg.encode("utf-8", "replace")
            # path can't be injected into since it's created in self.load
            # TODO: Catch PermissionError
            proc = subprocess.Popen([path, octets], env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)

            try: outs, errs = proc.communicate(octets + b"\n", timeout=6)
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

def serve(sockname, incoming):
    if os.path.exists(sockname):
        os.remove(sockname)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(sockname)
    sock.listen(1)

    def listen(sock):
        while True:
            connection, client = sock.accept()
            def handle(connection, client):
                try:
                    for octets in connection.makefile("rb"):
                        try:
                            text = octets.decode("ascii", "replace")
                            text = text.strip("\n")

                            if " " in text:
                                instruction, data = text.split(" ", 1)
                                args = generic.b64unpickle(data)
                            else:
                                instruction, args = text, tuple()

                            incoming.put((instruction,) + args)
                        except Exception as err:
                            debug("ERROR!", err.__class__.__name__, err)
                finally:
                    connection.close()
            generic.thread(handle, connection, client)
    generic.thread(listen, sock)

E_NO_PLUGINS = """
The plugins directory is necessary for saxo to work. If it was deleted
accidentally, just make a new empty directory and saxo will automatically
populate it with the core plugin that it needs to work.
"""

def start(base):
    generic.exit_cleanly()
    # http://stackoverflow.com/questions/11423225
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    plugins = os.path.join(base, "plugins")
    if not os.path.isdir(plugins):
        generic.error("no plugins directory: `%s`" % plugins, E_NO_PLUGINS)

    # TODO: Check for broken symlinks
    generic.populate(saxo_path, base)

    opt = configparser.ConfigParser()
    config = os.path.join(base, "config")
    opt.read(config)
    # TODO: defaulting?

    scripts = os.path.dirname(sys.modules["__main__"].__file__)
    scripts = os.path.abspath(scripts)

    sockname =  os.path.join(base, "client.sock")
    serve(sockname, incoming)
    os.chmod(sockname, 0o600)

    def remove_sock(sockname):
        os.remove(sockname)
    atexit.register(remove_sock, sockname)

    generic.thread(scheduler.start, base, incoming)

    saxo = Saxo(base, opt)
    saxo.run()
