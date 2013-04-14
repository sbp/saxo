# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import configparser
import os.path
import queue
import re
import socket
import subprocess
import sys

# Save PEP 3122!
if "." in __name__:
    from . import generic
else:
    import generic

incoming = queue.Queue()
outgoing = queue.Queue()

regex_optional_prefix = re.compile(r"(?::([^! ]*)!?([^@ ]*)@?([^ ]*))?")
regex_parameter = re.compile(r"((?:(?<= :)[^\r\n]*)|(?:[^: \r\n][^ \r\n]*))")

def parse(octets):
    text = octets.decode("utf-8", "replace")

    match_prefix = regex_optional_prefix.match(text)
    params = regex_parameter.findall(text[match_prefix.end():])
    return match_prefix.groups(), params[0], params[1:]

def socket_receive(sock):
    with sock.makefile("rb") as s:
        # TODO: How do we know when we're connected?
        incoming.put(("connected",))

        for octets in s:
            incoming.put(("remote", octets))

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

    generic.thread(socket_receive, sock)
    generic.thread(socket_send, sock)

def event(name):
    def decorate(function):
        event.registry[name] = function
        return function
    return decorate
event.registry = {}

@event("PING")
def ping(saxo, prefix, parameters):
    saxo.send("PONG", saxo.opt["client"]["nick"])

@event("PRIVMSG")
def exclamation(saxo, prefix, parameters):
    # ('nick', '~user', 'host') ['#channel', 'text']
    nick, user, host = prefix
    channel, text = tuple(parameters)

    if text == saxo.opt["client"]["nick"] + "!":
        saxo.send("PRIVMSG", channel, nick + "!")

@event(":connected")
def connected(saxo, prefix, parameters):
    saxo.send("NICK", saxo.opt["client"]["nick"])
    saxo.send("USER", saxo.opt["client"]["nick"], "+iw", saxo.opt["client"]["nick"], "saxo")
    for channel in saxo.opt["client"]["channels"].split(" "):
        saxo.send("JOIN", channel)

class Saxo(object):
    def __init__(self, base, opt):
        self.base = base
        self.opt = opt

    def send(self, *args):
        if len(args) > 1:
            args = args[:-1] + (":" + args[-1],)
        text = re.sub(r"[\r\n]", "", " ".join(args))
        outgoing.put(text.encode("utf-8", "replace")[:510] + b"\r\n")

def utf8(text):
    return text.encode("utf-8")

def start(base):
    opt = configparser.ConfigParser()
    config = os.path.join(base, "config")
    opt.read(config)

    scripts = os.path.dirname(sys.modules["__main__"].__file__)
    scripts = os.path.abspath(scripts)

    sockname =  os.path.join(base, "client.sock")
    generic.serve(sockname, incoming)

    # start_scheduler
    saxo_scheduler = os.path.join(scripts, "saxo-scheduler")
    scheduler = subprocess.Popen([saxo_scheduler, base])
    scheduler_pid = scheduler.pid

    connect(opt["server"]["host"], int(opt["server"]["port"]))

    saxo = Saxo(base, opt)

    while True:
        input = incoming.get()

        if input[0] == "connected":
            if ":connected" in event.registry:
                event.registry[":connected"](saxo, None, None)

        elif input[0] == "local":
            print("local", repr(input[1]))

        elif input[0] == "remote":
            octets = input[1]
            print(repr(octets))
            prefix, command, parameters = parse(octets)

            if command in event.registry:
                event.registry[command](saxo, prefix, parameters)

        else:
            print("?", input[0])
