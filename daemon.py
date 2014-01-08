# Copyright 2013-4, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import atexit
import os
import signal
import sys

def writeable(path):
    if os.path.exists(path):
        return os.access(path, os.W_OK)

    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        return False

    return os.access(directory, os.W_OK)

def fork(n):
    try: pid = os.fork()
    except OSError as err:
        print("Error: Unable to fork on this OS: %s" % err)
        print("Use the --foreground option to avoid running as a daemon")
        sys.exit(1)
    else:
        if pid > 0:
            sys.exit(0)

def redirect(a, b):
    os.dup2(b.fileno(), a.fileno())

def start(pidfile, output):
    if not writeable(pidfile):
        print("Error: Can't write to PID file: " + str(pidfile))
        sys.exit(1)

    fork(1)

    os.chdir("/")
    os.setsid()
    os.umask(0)

    fork(2)

    pid = os.getpid()

    print("Running saxo as PID %s" % pid)
    print("This PID is also saved in %s" % pidfile)

    sys.stdout.flush()
    sys.stderr.flush()

    redirect(sys.stdin, open(os.devnull, "r"))
    redirect(sys.stdout, output)
    redirect(sys.stderr, output)

    with open(pidfile, "w") as f:
        f.write(str(pid) + "\n")

    def delete_pidfile():
        if os.path.isfile(pidfile):
            os.remove(pidfile)
    atexit.register(delete_pidfile)

    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    return pid
