# Copyright 2013-4, Sean B. Palmer
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
    from . import common
    from . import scheduler
    from . import sqlite
    from .saxo import path as saxo_path
else:
    import common
    import scheduler
    import sqlite
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
# every process command, as a communication wrapper
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

class Message(object):
    def __init__(self, saxo, octets):
        prefix, command, parameters = parse(octets)

        self.base = saxo.base[:]
        self.config = saxo.config_cache.copy()

        self.nick = prefix[0]
        self.user = prefix[1]
        self.host = prefix[2]

        if self.nick and self.user and self.host:
            self.prefix = self.nick + "!" + self.user + "@" + self.host

        self.command = command
        self.parameters = parameters
        self.blocked = False

        def send(*args):
            saxo.send(*args)
        self.send = send

        def msg(*args):
            saxo.send("PRIVMSG", *args)
        self.msg = msg

        if self.command == "PRIVMSG":
            self.sender = self.parameters[0]
            self.text = self.parameters[1]
            self.private = self.sender == self.config["nick"]

            if self.private:
                self.sender = self.nick

            if saxo.address:
                # TODO: Why was this 498 for duxlot?
                self.limit = 493 - len(self.sender + saxo.address)

            def say(text):
                saxo.send("PRIVMSG", self.sender, text)
            self.say = say

            def reply(text):
                saxo.send("PRIVMSG", self.sender, self.nick + ": " + text)
            self.reply = reply

            private = self.config.get("private")
            if self.private:
                if private == "deny":
                    self.blocked = True
            elif private == "only":
                self.blocked = True

            self.cmd = None

            cmdpfx = self.config["prefix"]
            if self.text.startswith(cmdpfx):
                text = self.text[len(cmdpfx):]
                if " " in text:
                    cmd, arg = text.split(" ", 1)
                else:
                    cmd, arg = text, ""
                self.cmd = cmd
                self.arg = arg

    def client(self, *args):
        incoming.put(args)

# threaded
def socket_receive(sock):
    def receive_loop(sock, incoming):
        with sock.makefile("rb") as s:
            # TODO: How do we know when we're connected?
            incoming.put(("receiving",))
            for octets in s:
                incoming.put(("remote", octets))

    try: receive_loop(sock, incoming)
    except Exception as err:
        # Usually IOError, EOFError, socket.error, or ssl.SSLError
        ...
    incoming.put(("disco_receiving",))

# threaded
def socket_send(sock, flood=False):
    def sending(sock, flood=False):
        with sock.makefile("wb") as s:
            incoming.put(("sending",))
            while True:
                octets = outgoing.get()
                if octets is None:
                    debug("Sending Thread: Requested quit")
                    return True

                debug("->", repr(octets.decode("utf-8", "replace")))
                s.write(octets)
                s.flush()
                if not flood:
                    # TODO: Allow two or three burst lines
                    time.sleep(1)
        debug("Sending Thread: No more data")
        return False

    try: sending(sock, flood)
    except Exception as err:
        # Usually BrokenPipeError
        debug("Sending Thread: Error:", err)
    incoming.put(("disco_sending",))

class SaxoConnectionError(Exception):
    ...

class Saxo(object):
    def __init__(self, base, opt):
        self.base = base
        self.opt = opt
        self.events = {}
        self.address = None
        self.discotimer = None
        self.receiving = False
        self.sending = False
        self.receiving_thread = None
        self.sending_thread = None
        self.reconnecting = False
        self.links = {}

        self.environment_cache = os.environ.copy()
        self.environment_cache["PYTHONPATH"] = saxo_path
        # TODO: This needs to be changed when setting nick
        self.environment_cache["SAXO_BOT"] = opt["client"]["nick"]
        self.environment_cache["SAXO_BASE"] = base
        self.environment_cache["SAXO_COMMANDS"] = \
            os.path.join(base, "commands")

        self.config_cache = {}
        client_options = {
            "channels", # Channels to join on startup
            "nick", # Nickname of the bot, variable
            "owner", # Full address of the owner
            "prefix", # Command prefix
            "flood", # Whether or not to flood
            "private" # Whether to respond in private
        }

        for option in opt["client"]:
            if option in client_options:
                self.config_cache[option] = opt["client"].get(option)
            else:
                debug("Unknown option: %s" % option)

        for section in opt:
            if section == "client":
                continue
            self.config_cache[section] = dict(opt[section])

    def run(self):
        self.load()
        self.connect()
        self.handle()

    def load(self):
        # Update symlinks
        common.populate(saxo_path, self.base)

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

    def connect(self):
        try: self.connect_sock()
        except Exception as err:
           raise SaxoConnectionError(str(err))

        self.first = True
        # TODO: Reset other state? e.g. self.address

        receiving = (socket_receive, self.sock)
        self.receiving_thread = common.thread(*receiving)

        sending = (socket_send, self.sock, "flood" in self.opt["client"])
        self.sending_thread = common.thread(*sending)

    def connect_sock(self):
        host = self.opt["server"]["host"]
        port = int(self.opt["server"]["port"])

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if "ssl" in self.opt["server"]:
            import ssl
            debug("Warning: Using SSL, but not validating the cert!")
            self.sock = ssl.wrap_socket(
                self.sock,
                server_side=False,
                cert_reqs=ssl.CERT_NONE) # TODO: or CERT_REQUIRED

        debug("Connecting to %s:%s" % (host, port))
        self.sock.connect((host, port))

    def disconnect(self):
        # NOTE: *Do not* close the sending thread gracefully
        # The socket shutdown code below will be invoked before the queue
        # item reaches the socket thread. That means the *next* thread will
        # pick it up, because it'll quit with a pipe error anyway

        # Close the socket forcefully
        try: self.sock.shutdown(socket.SHUT_RDWR)
        except: ...

        try: self.sock.close()
        except: ...

        self.cancel_discotimer()

    def socket_threads_active(self):
        receiving = self.receiving_thread.is_alive()
        sending = self.sending_thread.is_alive()
        debug("RECV, SEND:", receiving, sending)
        return receiving or sending

    def cancel_discotimer(self):
        if self.discotimer is not None:
            try:
                was_finished = self.discotimer.finished.is_set()
                # Note: .cancel() still works on an expired timer!
                # It just calls .finished.set()
                self.discotimer.cancel()
                if not was_finished:
                    debug("Cancelled probably unfinished disco timer")
                self.discotimer = None
            except:
                ...

    def handle(self):
        while True:
            instruction_args = incoming.get()
            instruction = instruction_args[0]
            args = tuple(instruction_args[1:])

            if instruction not in {"instances", "remote"}:
                debug("handle:", instruction, args)

            if not isinstance(instruction, str):
                continue

            method_name = "instruction_" + instruction
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                try: method(*args)
                except Exception as err:
                    debug("handle error:", err)
                    # raise err # - for debug
            else:
                debug("Unknown instruction:", instruction)

    def instruction_address(self, address):
        self.address = address

    def instruction_connect(self, delay=5):
        # Warning: This quits the bot if the bot is already connected!
        # Use instruction_reconnect if you want to restart the bot

        # NOTE: The instruction mechanism is synchronous
        # This means we can't use self.receiving etc. to check connectivity
        # We rely on self.disconnect() to have done the right thing
        # The following is a check to make sure that it has
        if self.socket_threads_active():
            # Wait up to six seconds for the threads to quit
            for attempt in range(12):
                time.sleep(0.5)
                if not self.socket_threads_active():
                    break
            else:
                # TODO: If the threads are still active, they should be killed
                # Unfortunately, threads in python can't be killed
                debug("ERROR! Unable to stop the socket threads")
                os._exit(1)

        if "flood" not in self.opt["client"]:
            time.sleep(3)

        try: self.connect()
        except SaxoConnectionError as err:
            # Retry, with 1sec more delay, up to a maximum of 30sec delay
            def connect():
                incoming.put(("connect", min(30, delay + 1)))
            t = threading.Timer(delay, connect)
            t.start()

    def instruction_connected(self):
        if ":connected" in self.events:
            msg = Message(self, b"NOOP")
            for function in self.events[":connected"]:
                function(msg)

    def instruction_command(self, prefix, sender, cmd, arg):
        self.command(prefix, sender, cmd, arg)

    def instruction_disco_receiving(self):
        self.receiving = False
        if self.sending:
            outgoing.put(None)
        else:
            incoming.put(("connect",))

    def instruction_disco_sending(self):
        self.sending = False
        if self.receiving:
            self.disconnect()
        else:
            incoming.put(("connect",))

    def instruction_instances(self):
        our_pid = os.getpid()
        database_filename = os.path.join(self.base, "database.sqlite3")
        with sqlite.Database(database_filename) as db:
            pids = [row[0] for row in db["saxo_instances"]]
        if len(pids) == 1:
            if pids[0] == our_pid:
                return

        debug("Found another saxo instance! %s" % pids)
        self.send("QUIT", "Another saxo instance was detected")
        self.disconnect()
        os._exit(0)

    def instruction_join(self, channel):
        # NOTE: .visit can still be followed by .join
        # The JOIN will just fail on the server

        channels = self.opt["client"]["channels"].split(" ")
        if channel in channels:
            # TODO: .visit it back?
            return
        channels.append(channel)
        channels = " ".join(channels)

        self.update_config("client", "channels", channels)
        self.send("JOIN", channel)

    def instruction_link(self, channel, link):
        self.links[channel] = link

    def instruction_message(self, text):
        debug("IPC message:", text)

    def instruction_msg(self, destination, text):
        self.send("PRIVMSG", destination, text)

    def instruction_noop(self):
        ...

    def instruction_part(self, channel):
        # NOTE: .leave can still be followed by .part
        # The PART will just fail on the server

        channels = self.opt["client"]["channels"].split(" ")
        if channel not in channels:
            # TODO: .leave it anyway?
            return
        channels.remove(channel)
        channels = " ".join(channels)

        self.update_config("client", "channels", channels)
        self.send("PART", channel)

    def instruction_ping(self):
        now = time.time()

        # Don't ping if connected less than a minute ago
        if self.receiving > (now - 60):
            debug("Won't start discotimer, because we recently reconnected")
            return

        self.send("PING", self.opt["client"]["nick"])

        def reconnect():
            incoming.put(("reconnect",))

        # Make sure the timer is shorter than the pingloop!
        # Default pingloop period is 180
        self.discotimer = threading.Timer(30, reconnect)
        self.discotimer.start()

    def instruction_prefix(self, pfx):
        self.update_config("client", "prefix", pfx)

    def instruction_quit(self):
        # Never call this from a thread, otherwise this can give an OSError
        # TODO: Get the sender to pick this up and disconnect from there?
        # Could be a problem if the sender has broken
        self.send("QUIT")
        self.disconnect()
        # sys.exit()
        # TODO: Sometimes sys.exit doesn't work, not sure why
        os._exit(0)

    def instruction_receiving(self):
        self.receiving = time.time()
        # TODO: Check that we really are connected
        # TODO: Unit test for :connected event
        incoming.put(("connected",))

    def instruction_reconnect(self):
        # disco_* will automatically reconnect
        if self.receiving or self.receiving_thread.is_alive():
            # Close the socket, which forces the receiving thread to quit
            self.disconnect()
        elif self.sending or self.sending_thread.is_alive():
            # Signal the sending thread to quit
            outgoing.put(None)
        else:
            debug("Reconnect requested during reconnect")

    def instruction_reload(self, destination=None):
        before = time.time()
        self.load()
        elapsed = time.time() - before
        if destination:
            self.send("PRIVMSG", destination,
                "Reloaded in %s seconds" % round(elapsed, 3))

    def instruction_remote(self, octets):
        debug(repr(octets))
        msg = Message(self, octets)

        if msg.command == "PRIVMSG":
            if msg.blocked:
                return

            if msg.cmd is not None:
                self.command(msg)

        elif msg.command == "PONG":
            self.cancel_discotimer()

        def run(name, msg):
            if name in self.events:
                for function in self.events[name]:
                    try: function(msg)
                    except Exception as err:
                        debug("Error:", function.__name__ + ":", err)

        if self.first is True:
            run(":1st", msg)
            self.first = False

        run(msg.command, msg)
        run("*", msg)

    def instruction_schedule(self, unixtime, command, args):
        command = command.encode("ascii")
        args = common.b64pickle(args)
        scheduler.incoming.put((unixtime, command, args))

    def instruction_send(self, *args):
        self.send(*args)

    def instruction_sending(self):
        self.sending = True

    def command(self, msg):
        cmd, arg = msg.cmd, msg.arg

        if ("\x00" in cmd) or (os.sep in cmd) or ("." in cmd):
            return

        path = os.path.join(self.base, "commands", cmd)

        def process(env, path, arg):
            octets = arg.encode("utf-8", "replace")

            try: proc = subprocess.Popen([path, octets], env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            except PermissionError:
                outs = "The command file does not have executable permissions"
            except FileNotFoundError:
                # Might have been removed just after running this thread
                return
            else:
                try: outs, errs = proc.communicate(octets + b"\n", timeout=12)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    # TODO: Use actual prefix
                    outs = "Sorry, %s took too long" % cmd
                else:
                    outs = outs.decode("utf-8", "replace")
                    if "\n" in outs:
                        outs = outs.splitlines()[0]

                code = proc.returncode or 0
                # Otherwise: TypeError: unorderable types: NoneType() > int()
                if (code > 0) and (not outs):
                    # TODO: Use actual prefix
                    outs = "Sorry, %s responded with an error" % cmd

            if outs:
                self.send("PRIVMSG", msg.sender, outs)

        if os.path.isfile(path):
            env = self.environment_cache.copy()
            env["SAXO_NICK"] = msg.nick
            env["SAXO_SENDER"] = msg.sender
            if msg.sender in self.links:
                env["SAXO_URL"] = self.links[msg.sender]
            common.thread(process, env, path, arg)

    def update_config(self, section, option, value):
        self.opt[section][option] = value
        config = os.path.join(self.base, "config")
        with open(config, "w", encoding="utf-8") as f:
            self.opt.write(f)
        if section == "client":
            self.config_cache[option] = value
        else:
            self.config_cache[section][option] = value
        # TODO: Change the database

    def send(self, *args):
        # TODO: Loop detection
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
                                args = common.b64unpickle(data)
                            else:
                                instruction, args = text, tuple()

                            incoming.put((instruction,) + args)
                        except Exception as err:
                            debug("ERROR!", err.__class__.__name__, err)
                finally:
                    connection.close()
            common.thread(handle, connection, client)
    common.thread(listen, sock)

E_NO_CONFIG = """
Are you sure this is a saxo configuration directory? If you need to make a new
configuration directory, use the `saxo create` command.
"""

def start(base):
    # TODO: Check when two clients are running
    common.exit_cleanly()
    # http://stackoverflow.com/questions/11423225
    # IGN rather than DFL, otherwise Popen.communicate can quit saxo
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)

    opt = configparser.ConfigParser(interpolation=None)
    config = os.path.join(base, "config")
    if not os.path.isfile(config):
        error("missing config file in: `%s`" % config, E_NO_CONFIG)
    opt.read(config)
    # TODO: Defaulting?
    # TODO: Warn if the config file is widely readable?

    common.populate(saxo_path, base)

    sockname =  os.path.join(base, "client.sock")
    serve(sockname, incoming)
    os.chmod(sockname, 0o600)

    # NOTE: If using os._exit, this doesn't work
    def remove_sock(sockname):
        if os.path.exists(sockname):
            os.remove(sockname)
    atexit.register(remove_sock, sockname)

    common.thread(scheduler.start, base, incoming)

    saxo = Saxo(base, opt)
    saxo.run()
