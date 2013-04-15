# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

# You know your code is good when you have a generic module

import os
import signal
import socket
import sys
import threading

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
        sys.exit()

    signal.signal(signal.SIGINT, quit)
    signal.signal(signal.SIGTERM, quit)

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
                        incoming.put(("local", octets))
                finally:
                    connection.close()
            thread(handle, connection, client)
    thread(listen, sock)

def thread(target, *args):
    t = threading.Thread(target=target, args=tuple(args), daemon=True)
    t.start()
