# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import argparse
import os.path
import sys

def error(short, long=None, err=None):
    print("saxo: error: " + short, file=sys.stderr)

    if long is not None:
        print(long.rstrip(), file=sys.stderr)

    if err is not None:
        if long is not None:
            print("", file=sys.stderr)

        print("This is the error message that python gave:", file=sys.stderr)
        print("", file=sys.stderr)
        print("    %s" % err.__class__.__name__)
        print("        %s" % err)
    sys.exit(1)

E_PYTHON_VERSION = """
Your version of the python programming language is too old to run saxo. Use a
newer version if available. Otherwise you can get a newer version from here:

    http://www.python.org/

Or install one using your system's package manager. If you are using OS X for
example, python3 can be installed using homebrew:

    http://mxcl.github.io/homebrew/
"""

if sys.version_info < (3, 3):
    error("requires python 3.3 or later", E_PYTHON_VERSION)

def action(function):
    action.names[function.__name__] = function
    return function
action.names = {}

# Options

def version(args):
    print("saxo alpha")

USAGE = """
Usage:
    saxo -v
    saxo create [ directory ]
    saxo [ -f ] [ -o filename ] start [ directory ]
    saxo stop [ directory ]
    saxo active [ directory ]

Try `saxo -h` for more detailed usage
"""

def usage(args):
    version(args)
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

def help(args):
    version(args)
    print(HELP.rstrip())

# Actions

@action
def create(args):
    # Save PEP 3122!
    if "." in __name__:
        from . import create
    else:
        import create

    # def default(directory=None)
    # — create.py
    create.default(args.directory)
    return 0

@action
def start(args):
    print("Can't start a bot yet")
    if not args.foreground:
        # Save PEP 3122!
        if "." in __name__:
            from . import daemon
        else:
            import daemon

        if args.directory is None:
            args.directory = os.path.expanduser("~/.saxo")

        if args.output is None:
            output = open(os.devnull, "w")
        elif args.output in {"-", "/dev/stdout"}:
            output = sys.stdout
        else:
            output = open(args.output, "w")

        pidfile = os.path.join(args.directory, "pid")
        daemon.start(pidfile, output)
    return 0

@action
def stop(args):
    print("Can't start a bot yet")
    return 0

def main(argv):
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
        help(args)

    elif args.version:
        version(args)

    elif args.action:
        if args.action in action.names:
            code = action.names[args.action](args)
            if isinstance(code, int):
                sys.exit(code)
        else:
            error("unrecognised action: %s" % args.action)
            # TODO: Should really exit 2

    else:
        usage(args)
