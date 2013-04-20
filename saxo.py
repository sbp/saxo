# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

version = "0.1.004"
# WARNING: If updating anything before this message,
# change the offset in setup.py

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

# monitor (post) - event priority low?
# doesn't really matter since they're threaded...
# environment

def command(name):
    def decorate(function):
        @event("PRIVMSG")
        def inner(irc):
            prefix = irc.client["prefix"]
            if irc.text.startswith(prefix):
                length = len(prefix)
                text = irc.text[length:]

                if " " in text:
                    cmd, arg = text.split(" ", 1)
                else:
                    cmd, arg = text, ""

                if cmd == name:
                    irc.arg = arg
                    function(irc)
        return inner
    return decorate

def communicate(command, args, base=None):
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

# TODO: Can't call this saxo.database, because the import sets that attribute
def db(name=None):
    import os

    # Save PEP 3122!
    if "." in __name__:
        from .database import Database
    else:
        from database import Database

    if name is None:
        base = os.environ["SAXO_BASE"]
        name = os.path.join(base, "database.sqlite3")

    return Database(name)

# TODO: priority?
def event(command="*", synchronous=False):
    def decorate(function):
        function.saxo_event = command
        function.saxo_synchronous = synchronous
        return function
    return decorate

# TODO: pipe is somewhat of a misnomer since it uses argv[1] now
def pipe(function):
    # This gives you concise code, clean exiting, and a custom error wrapper
    # TODO: Would like to run this in caller __name__ == "__main__"
    # __name__ here is "saxo"
    import sys

    # Save PEP 3122!
    if "." in __name__:
        from . import generic
    else:
        import generic

    generic.exit_cleanly()
    arg = sys.argv[1]

    try: result = function(arg)
    except Exception as err:
        import os.path
        import traceback

        python = err.__class__.__name__ + ": " + str(err)
        stack = traceback.extract_tb(err.__traceback__, limit=2)
        item = stack.pop()
        where = "(%s:%s)" % (os.path.basename(item[0]), item[1])
        result = python + " " + where

    if result is not None:
        sys.stdout.write(result + "\n")

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
