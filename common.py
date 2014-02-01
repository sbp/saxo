# http://inamidst.com/saxo/
# Created by Sean B. Palmer

# You know your code is good when you don't have a generic module

import base64
import collections
import os
import pickle
import signal
import socket
import sys
import threading

# Usage as of 534f8c68:
# b64pickle: client
# b64unpickle: client, scheduler
# error: client, create, script
# exit_cleanly: client, saxo
# populate: client, create
# thread: client, script

def console():
    # TODO: This can probably be removed
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client_sock = os.path.expanduser("~/.saxo/client.sock")
    client.connect(client_sock)

    while True:
        try: text = input("$ ")
        except (EOFError, KeyboardInterrupt):
            print("")
            print("Quitting...")
            break

        if " " in text:
            instruction, args = text.split(" ", 1)
            if args:
                args = eval("(%s,)" % args)
                args = b64pickle(args)
        else:
            instruction, args = text, b""

        octets = instruction.encode("ascii") + b" " + args
        client.send(octets + b"\n")

def error(short, long=None, err=None, code=1):
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
    sys.exit(code)

def exit_cleanly():
    def quit(signum, frame):
        print("Exiting cleanly (SIG %s)" % signum)
        try: sys.exit()
        finally: os._exit(0)

    signal.signal(signal.SIGINT, quit)
    signal.signal(signal.SIGTERM, quit)

def populate(saxo_path, base):
    # TODO: This is being called twice
    plugins = os.path.join(base, "plugins")
    saxo_plugins = os.path.join(saxo_path, "plugins")
    if not os.path.isdir(plugins):
        os.mkdir(plugins)

    commands = os.path.join(base, "commands")
    saxo_commands = os.path.join(saxo_path, "commands")
    if not os.path.isdir(commands):
        os.mkdir(commands)

    def symlink(source, dest):
        try: os.symlink(source, dest)
        except FileExistsError:
            ...

    for name in os.listdir(saxo_plugins):
        dest = os.path.join(plugins, name)
        if not (os.path.exists(dest) or os.path.islink(dest)):
            symlink(os.path.join(saxo_plugins, name), dest)

    with open(os.path.join(commands, "saxo.pth"), "w") as f:
        f.write(saxo_path + "\n")

    old_path_file = os.path.join(commands, ".saxo-path")
    if os.path.islink(old_path_file):
        os.remove(old_path_file)

    for name in os.listdir(saxo_commands):
        dest = os.path.join(commands, name)
        if not (os.path.exists(dest) or os.path.islink(dest)):
            symlink(os.path.join(saxo_commands, name), dest)

    # Clean up any broken symlinks
    for directory in (plugins, commands):
        for name in os.listdir(directory):
            link = os.path.join(directory, name)
            if not os.path.islink(link):
                continue

            target = os.readlink(link)
            target = os.path.join(directory, target)
            if not os.path.exists(target):
                os.remove(link)

def b64pickle(obj):
    pickled = pickle.dumps(obj)
    return base64.b64encode(pickled)

def b64unpickle(data):
    if data:
        pickled = base64.b64decode(data)
        return pickle.loads(pickled)
    return tuple()

def thread(target, *args):
    t = threading.Thread(target=target, args=tuple(args), daemon=True)
    t.start()
    return t

def tarjan(graph):
    # Robert E. Tarjan's 1975 strongly connected nodes algorithm
    # This is a kind of robust topological sort
    index = {}
    lowlinks = {}
    stack = collections.OrderedDict()
    result = []

    def search(node):
        index[node] = len(index)
        lowlinks[node] = index[node]
        stack[node] = None

        for succ in graph.get(node, ()):
            if succ not in index:
                search(succ)
                lowlinks[node] = min(lowlinks[succ], lowlinks[node])
            elif succ in stack:
                lowlinks[node] = min(lowlinks[node], index[succ])

        if lowlinks[node] == index[node]:
            connected = []
            succ = None
            while succ != node:
                succ = stack.popitem()[0]
                connected.append(succ)
            result.append(connected)

    for node in graph:
        if not node in index:
            search(node)
    return result

def tsort(graph):
    for connected in tarjan(graph):
        for node in connected:
            yield node
