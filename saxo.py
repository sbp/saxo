# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

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

# TODO: priority?
def event(command="*", synchronous=False):
    def decorate(function):
        function.saxo_event = command
        function.saxo_synchronous = synchronous
        return function
    return decorate

def pipe(function):
    # __name__ is "saxo"
    import resource
    import sys

    # Save PEP 3122!
    if "." in __name__:
        from . import generic
    else:
        import generic

    generic.exit_cleanly()
    resource.setrlimit(resource.RLIMIT_CPU, (6, 6))

    for line in sys.stdin:
        try: result = function(line.rstrip("\n"))
        except Exception as err:
            import os.path
            import traceback

            python = err.__class__.__name__ + ": " + str(err)
            stack = traceback.extract_tb(err.__traceback__, limit=2)
            item = stack.pop()
            where = "(%s:%s)" % (os.path.basename(item[0]), item[1])
            result = python + " " + where
        break

    sys.stdout.write(result + "\n")

def setup(function):
    function.saxo_setup = True
    return function

def script(argv):
    # Save PEP 3122!
    if "." in __name__:
        from .script import main
    else:
        from script import main
    main(argv)
