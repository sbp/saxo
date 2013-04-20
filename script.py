# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import argparse
import os.path
import signal
import sys
import time

# Save PEP 3122!
if "." in __name__:
    from . import generic
else:
    import generic

E_PYTHON_VERSION = """
Your version of the python programming language is too old to run saxo. Use a
newer version if available. Otherwise you can get a newer version from here:

    http://www.python.org/

Or install one using your system's package manager. If you are using OS X for
example, python3 can be installed using homebrew:

    http://mxcl.github.io/homebrew/
"""

try: import sqlite3
except ImportError:
    print("Error: sqlite3 is not installed", file=sys.stderr)
    print("Please build Python against the sqlite libraries", file=sys.stderr)
    sys.exit(1)
else:
    if not sqlite3.threadsafety:
        print("Error: Your sqlite3 is not thread-safe", file=sys.stderr)
        sys.exit(1)

if sys.version_info < (3, 3):
    generic.error("requires python 3.3 or later", E_PYTHON_VERSION)

def action(function):
    action.names[function.__name__] = function
    return function
action.names = {}

# Options

def version(args, v):
    print("saxo %s" % v)

USAGE = """
Usage:
    saxo -v
    saxo create [ directory ]
    saxo [ -f ] [ -o filename ] start [ directory ]
    saxo stop [ directory ]
    saxo active [ directory ]

Try `saxo -h` for more detailed usage
"""

def usage(args, v):
    version(args, v)
    print(USAGE.rstrip())

HELP = """
Usage:

    saxo -v / --version
        Show the current saxo version

    saxo create [ directory ]
        Create a default configuration file

    saxo [ Options ] start [ directory ]
        Starts a bot. Options:

            -f / --foreground
                Don't run the bot as a daemon

            -o / --output filename
                Redirect stdout and stderr to filename

    saxo stop [ directory ]
        Stops a bot

    saxo active [ directory ]
        Shows whether a bot is active
"""

def help(args, v):
    version(args, v)
    print(HELP.rstrip())

# Actions

@action
def create(args):
    # Save PEP 3122!
    if "." in __name__:
        from . import create
    else:
        import create

    # def default(base=None)
    # — create.py
    create.default(args.directory)
    return 0

@action
def start(args):
    if args.directory is None:
        directory = os.path.expanduser("~/.saxo")
    else:
        directory = args.directory

    if not args.foreground:
        # Save PEP 3122!
        if "." in __name__:
            from . import daemon
        else:
            import daemon

        if args.output is None:
            output = open(os.devnull, "w")
        elif args.output in {"-", "/dev/stdout"}:
            output = sys.stdout
        else:
            output = open(args.output, "w")

        pidfile = os.path.join(directory, "pid")
        daemon.start(pidfile, output)

    # Save PEP 3122!
    if "." in __name__:
        from . import client
    else:
        import client

    client.start(directory)
    return 0

@action
def stop(args):
    if args.directory is None:
        directory = os.path.expanduser("~/.saxo")
    else:
        directory = args.directory

    pidfile = os.path.join(directory, "pid")
    if not os.path.exists(pidfile):
        generic.error("There is no bot currently running")

    with open(pidfile, encoding="ascii") as f:
        text = f.read()
        pid = int(text.rstrip("\n"))

    # TODO: Make this less crude
    os.kill(pid, signal.SIGTERM)
    # os.kill(pid, signal.SIGKILL)

    return 0

def main(argv, v):
    # NOTE: No default for argv, because what script name would we use?

    parser = argparse.ArgumentParser(description="Control saxo irc bot instances",
        add_help=False)

    parser.add_argument("-f", "--foreground", action="store_true",
        help="run in the foreground instead of as a daemon")

    parser.add_argument("-h", "--help", action="store_true",
        help="show a short help message")

    parser.add_argument("-o", "--output", metavar="filename",
        help="redirect daemon stdout and stderr to this filename")

    parser.add_argument("-v", "--version", action="store_true",
        help="show the current saxo version")

    parser.add_argument("action", nargs="?",
        help="use --help to show the available actions")

    parser.add_argument("directory", nargs="?",
        help="the path to the saxo configuration directory")

    args = parser.parse_args(argv[1:])

    if args.help:
        help(args, v)

    elif args.version:
        version(args, v)

    elif args.action:
        if args.action in action.names:
            code = action.names[args.action](args)
            if isinstance(code, int):
                sys.exit(code)
        else:
            generic.error("unrecognised action: %s" % args.action, code=2)

    else:
        usage(args, v)
