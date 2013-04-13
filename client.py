# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import configparser
import os.path
import queue
import re
import socket
import sys
import threading

incoming = queue.Queue()
outgoing = queue.Queue()

regex_optional_prefix = re.compile(r"(?::([^! ]*)!?([^@ ]*)@?([^ ]*))?")
regex_parameter = re.compile(r"((?:(?<= :)[^\r\n]*)|(?:[^: \r\n][^ \r\n]*))")

def parse(octets):
    text = octets.decode("utf-8", "replace")

    match_prefix = regex_optional_prefix.match(text)
    params = regex_parameter.findall(text[match_prefix.end():])
    return match_prefix.groups(), params[0], params[1:]

def thread(target, *args):
    t = threading.Thread(target=target, args=tuple(args))
    t.start()

def socket_receive(sock):
    with sock.makefile("rb") as s:
        # TODO: How do we know when we're connected?
        incoming.put(("connected",))

        for octets in s:
            incoming.put(("received", octets))

def socket_send(sock):
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

    thread(socket_receive, sock)
    thread(socket_send, sock)

def event(name):
    def decorate(function):
        event.registry[name] = function
        return function
    return decorate
event.registry = {}

@event("PING")
def ping(opt, prefix, parameters):
    send("PONG", opt["client"]["nick"])

@event("PRIVMSG")
def exclamation(opt, prefix, parameters):
    # ('nick', '~user', 'host') ['#channel', 'text']
    nick, user, host = prefix
    channel, text = tuple(parameters)

    if text == opt["client"]["nick"] + "!":
        send("PRIVMSG", channel, nick + "!")

def send(*args):
    if len(args) > 1:
        args = args[:-1] + (":" + args[-1],)
    text = re.sub(r"[\r\n]", "", " ".join(args))
    outgoing.put(text.encode("utf-8", "replace")[:510] + b"\r\n")

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
                        incoming.put(("command", octets))
                finally:
                    connection.close()
            thread(handle, connection, client)
    thread(listen, sock)

    while True:
        input = incoming.get()

        if input[0] == "connected":
            send("NICK", opt["client"]["nick"])
            send("USER", opt["client"]["nick"], "+iw", opt["client"]["nick"], "saxo")
            for channel in opt["client"]["channels"].split(" "):
                send("JOIN", channel)

        elif input[0] == "command":
            print("got command")

        elif input[0] == "received":
            octets = input[1]
            print(repr(octets))
            prefix, command, parameters = parse(octets)

            if command in event.registry:
                event.registry[command](opt, prefix, parameters)

        else:
            print("?", input[0])

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
