# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

version = "0.2.004"
# WARNING: If updating anything before this message,
# change the offset in setup.py

# TODO list:
# - Think about folding common.py into saxo.py
# - Allow wildcards in [client].owner
# - Implement [plugins].sync, copy or symlink as options
# - Document the saxo, irc, self, and instruction interfaces
# - Think about a packaging system
# - Maybe write up a little guide to installing py3.3 with sqlite support
# - Allow JSON submission to the socket IPC interface
# - Write docstrings for all the public interfaces
# - Allow multiple, possibly configurable, lines of output from commands?
# - Plugins for pre_exec?
# - Make it possible to set periodic commands
# - Make sure the test server exits correctly
# - Dump a copy of the initialised config to the database
# - Document the database tables
# - Delete and select methods for sqlite.Table

path = None

if "__file__" in vars():
    if __file__:
        import os.path

        path = os.path.abspath(__file__)
        path = os.path.realpath(path)
        path = os.path.dirname(path)

        del os

if "__path__" in vars():
    if __path__:
        for directory in __path__:
            if path is None:
                path = directory
            elif path != directory:
                raise Exception("Can't create saxo.path")

        del directory

# Decorators:
#
# saxo.command(name)
# saxo.event(command="*", synchronous=False)
# saxo.pipe(function)
# saxo.setup(function)
#
# Other:
#
# saxo.client(command, *args, base=None)
# saxo.database(name=None)
# saxo.env(name)
# saxo.request(*args, **kargs)
# saxo.script(argv)

# TODO: environment modification?

def client(command, *args, base=None):
    import base64
    import os
    import pickle
    import socket

    if base is None:
        base = os.environ["SAXO_BASE"]

    sockname = os.path.join(base, "client.sock")
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(sockname)

    command = command.encode("ascii", "replace")
    pickled = pickle.dumps(args)
    client.send(command + b" " + base64.b64encode(pickled) + b"\n")
    client.close()

def command(name, owner=False):
    def is_owner(irc):
        config_owner = irc.config["owner"]
        test_identity = False
        if not "!" in config_owner:
            test_identity = True
            config_owner = config_owner + "!*@*"

        mask = lambda g: "^" + re.escape(g).replace("\\*", ".*") + "$"
        matches = re.match(mask(config_owner), irc.prefix) is not None
        if test_identity:
           return matches and irc.identified
        return matches

    def decorate(function):
        @event("PRIVMSG")
        def inner(irc):
            prefix = irc.config["prefix"]
            if irc.text.startswith(prefix):
                length = len(prefix)
                text = irc.text[length:]

                if " " in text:
                    cmd, arg = text.split(" ", 1)
                else:
                    cmd, arg = text, ""

                if cmd == name:
                    irc.arg = arg
                    if (not owner) or is_owner(irc):
                        function(irc)
        return inner
    return decorate

# saxo_event
# saxo_periodic
# saxo_private
# saxo_schedule
# saxo_seen
# saxo_setup
# saxo_to
# saxo_unicode

def database(name=None):
    import os

    # Save PEP 3122!
    if "." in __name__:
        from .sqlite import Database
    else:
        from sqlite import Database

    if name is None:
        base = os.environ["SAXO_BASE"]
        name = os.path.join(base, "database.sqlite3")

    return Database(name)

# saxo.env("base")
# saxo.env("bot")
# saxo.env("commands")
# saxo.env("nick")
# saxo.env("sender")
# saxo.env("url")

def env(name, alternative=None):
    import os
    return os.environ.get("SAXO_%s" % name.upper(), alternative)

# TODO: priority?
def event(command="*", synchronous=False):
    def decorate(function):
        function.saxo_event = command
        function.saxo_synchronous = synchronous
        return function
    return decorate

def pipe(function):
    # This gives you:
    # * concise code
    # * clean exiting
    # * input surrogate decoding
    # * output encoding
    # * a custom error wrapper

    # TODO: Would like to run this in caller __name__ == "__main__"
    # __name__ here is "saxo"
    import os
    import sys

    # Save PEP 3122!
    if "." in __name__:
        from . import common
    else:
        import common

    common.exit_cleanly()

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        # We have to do this because python converts arguments to surrogates
        # http://stackoverflow.com/a/7077803
        arg = os.fsencode(arg).decode("utf-8")
    elif not sys.stdin.isatty():
        arg = sys.stdin.buffer.readline()
        arg = arg.rstrip(b"\r\n")
    else:
        arg = ""

    try: result = function(arg)
    except Exception as err:
        import os.path
        import traceback

        python = err.__class__.__name__ + ": " + str(err)
        stack = traceback.extract_tb(err.__traceback__)
        # limit frame to command module
        filename = stack[1][0]
        line_number = "?"
        for frame in stack:
            if frame[0] == filename:
                line_number = frame[1]
            elif line_number != "?":
                break
        where = "(%s:%s)" % (os.path.basename(filename), line_number)
        result = python + " " + where

    if result is not None:
        if not isinstance(result, str):
            print("Error: expected str, got %s" % type(result))
            return
        result = result.encode("utf-8", "replace")
        sys.stdout.buffer.write(result + b"\n")
        sys.stdout.flush()

def request(*args, **kargs):
    # Save PEP 3122!
    if "." in __name__:
        from . import web
    else:
        import web

    return web.request(*args, **kargs)

def setup(function):
    function.saxo_setup = True
    return function

def script(argv):
    # Save PEP 3122!
    if "." in __name__:
        from .script import main
    else:
        from script import main

    main(argv, version)
