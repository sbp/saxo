# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import argparse
import codecs
import os
import signal
import sys
import time

# Save PEP 3122!
if "." in __name__:
    from . import common
else:
    import common

sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

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
    common.error("requires python 3.3 or later", E_PYTHON_VERSION)

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
def shell(args):
    if args.directory is None:
        base = os.path.expanduser("~/.saxo")
    else:
        base = args.directory

    # Save PEP 3122!
    if "." in __name__:
        from .saxo import path as saxo_path
    else:
        from saxo import path as saxo_path

    def subshell(base, commands):
        path = os.environ.get("PATH", "")
        os.environ["PATH"] = commands + os.pathsep + path
        os.environ["PYTHONPATH"] = saxo_path
        os.environ["SAXO_SHELL"] = "1"
        os.environ["SAXO_BASE"] = base
        os.environ["SAXO_BOT"] = "saxo"
        os.environ["SAXO_COMMANDS"] = commands
        os.environ["SAXO_NICK"] = os.environ["USER"]
        os.environ["SAXO_SENDER"] = os.environ["USER"]
        shell = os.environ.get("SHELL", "sh")
        os.system(shell)

    commands = os.path.join(base, "commands")
    subshell(base, commands)
    return 0

@action
def start(args):
    if args.directory is None:
        base = os.path.expanduser("~/.saxo")
    else:
        base = args.directory

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

        pidfile = os.path.join(base, "pid")
        daemon.start(pidfile, output)

    # Save PEP 3122!
    if "." in __name__:
        from . import irc
    else:
        import irc

    irc.start(base)
    return 0

@action
def stop(args):
    if args.directory is None:
        base = os.path.expanduser("~/.saxo")
    else:
        base = args.directory

    pidfile = os.path.join(base, "pid")
    if not os.path.exists(pidfile):
        common.error("There is no bot currently running")

    with open(pidfile, encoding="ascii") as f:
        text = f.read()
        pid = int(text.rstrip("\n"))

    # TODO: Make this less crude
    os.kill(pid, signal.SIGTERM)
    # os.kill(pid, signal.SIGKILL)

    return 0

@action
def test(args):
    if args.directory is not None:
        common.error("Tests cannot be run in conjunction with a directory")

    import queue
    import shutil
    import subprocess
    import tempfile

    # Save PEP 3122!
    if "." in __name__:
        from . import saxo
    else:
        import saxo

    saxo_script = sys.modules["__main__"].__file__
    saxo_test_server = os.path.join(saxo.path, "test", "server.py")

    tmp = tempfile.mkdtemp()
    outgoing = queue.Queue()

    if not sys.executable:
        common.error("Couldn't find the python executable")

    if not os.path.isdir(tmp):
        common.error("There is no %s directory" % tmp)

    print("python executable:", sys.executable)
    print("saxo path:", saxo.path)
    print("saxo script:", saxo_script)
    print("saxo test server:", saxo_test_server)
    print()

    def run_server():
        server = subprocess.Popen([sys.executable, "-u", saxo_test_server],
            stdout=subprocess.PIPE)

        for line in server.stdout:
            line = line.decode("utf-8", "replace")
            line = line.rstrip("\n")
            outgoing.put("S: " + line)

        outgoing.put("Server finished")

    def run_client():
        saxo_test = os.path.join(tmp, "saxo-test")
        outgoing.put("Running in %s" % saxo_test)

        cmd = [sys.executable, saxo_script, "create", saxo_test]
        code = subprocess.call(cmd)
        if code:
            print("Error creating the client configuration")
            sys.exit(1)

        test_config = os.path.join(saxo.path, "test", "config")
        saxo_test_config = os.path.join(saxo_test, "config")
        shutil.copy2(test_config, saxo_test_config)

        client = subprocess.Popen([sys.executable, "-u",
                saxo_script, "-f", "start", saxo_test],
            stdout=subprocess.PIPE)

        for line in client.stdout:
            line = line.decode("utf-8", "replace")
            line = line.rstrip("\n")
            outgoing.put("C: " + line)

        manifest01 = {"commands", "config", "database.sqlite3", "plugins"}
        manifest02 = manifest01 | {"client.sock"}

        if set(os.listdir(saxo_test)) == manifest01:
            shutil.rmtree(saxo_test)
        elif set(os.listdir(saxo_test)) == manifest02:
            outgoing.put("Warning: client.sock was not removed")
            shutil.rmtree(saxo_test)
        else:
            outgoing.put("Refusing to delete the saxo test directory")
            outgoing.put("Data was found which does not match the manifest")
            outgoing.put(saxo_test)

    common.thread(run_server)
    common.thread(run_client)

    error = False
    completed = False
    client_buffer = []
    while True:
        line = outgoing.get()

        if line.startswith("S: "):
            print(line)
            if line.startswith("S: ERROR"):
               error = True
            if line.startswith("S: Tests complete"):
               completed = True
            if not line.startswith("S: Test"):
                for c in client_buffer:
                    print(c)
            del client_buffer[:]

        elif line.startswith("C: "):
            client_buffer.append(line)

        else:
            print(line)

        sys.stdout.flush()

        if line == "Server finished":
            break

    if completed and (not error):
        sys.exit(0)
    else:
        sys.exit(1)

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
            common.error("unrecognised action: %s" % args.action, code=2)

    else:
        usage(args, v)
