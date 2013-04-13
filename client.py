# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import configparser
import os.path
import queue
import socket
import sys
import threading

incoming = queue.Queue()
outgoing = queue.Queue()

def thread(target, *args):
    t = threading.Thread(target=target, args=tuple(args))
    t.start()

def receive(sock):
    with sock.makefile("rb") as s:
        # TODO: How do we know when we're connected?
        incoming.put("Connected")

        for octets in s:
            incoming.put(octets)

def send(sock):
    with sock.makefile("wb") as s:
        while True:
            octets = outgoing.get()
            print("->", repr(octets.decode("ascii")))
            s.write(octets)
            s.flush()

def connect(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("Connecting to %s:%s" % (host, port))
    sock.connect((host, port))

    thread(receive, sock)
    thread(send, sock)

def utf8(text):
    return text.encode("utf-8")

def serve(base, opt):
    sockname =  os.path.join(base, "client.sock")
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
                        incoming.put(octets)
                finally:
                    connection.close()
            thread(handle, connection, client)
    thread(listen, sock)

    while True:
        octets = incoming.get()
        if octets == "Connected":
            import random
            n = random.randrange(0, 100000)
            outgoing.put(utf8("NICK saxo%05i\r\n" % n))
            outgoing.put(utf8("USER saxo%05i +iw saxo%05i saxo\r\n" % (n, n)))
            for channel in opt["client"]["channels"].split(" "):
                outgoing.put(utf8("JOIN %s\r\n" % channel))
        else:
            text = octets.decode("utf-8", "replace")
            print(repr(text))

def start(base):
    print("BASE:", base)

    config = os.path.join(base, "config")

    opt = configparser.ConfigParser()
    opt.read(config)

    scripts = os.path.dirname(sys.modules["__main__"].__file__)
    scripts = os.path.abspath(scripts)
    print("SCRIPTS:", scripts)

    connect(opt["server"]["host"], int(opt["server"]["port"]))
    serve(base, opt)
