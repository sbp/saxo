# Copyright 2012-4, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import codecs
import multiprocessing
import os
import re
import socket
import socketserver
import sys
import time

sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

scripts = os.path.dirname(sys.modules["__main__"].__file__)
scripts = os.path.abspath(scripts)

sys.path[:0] = [scripts, os.getcwd()]

connections = 0
test_counter = 0
tests = {}

def test(test_function):
    global test_counter

    def decorated(conn):
        test_function(conn)

    test_counter += 1
    decorated.number = test_counter
    tests[decorated.number] = decorated
    return decorated

# @@ quit from a test, then start a new instance

@test
def test_initial_ping(conn):
    conn.handshake()
    conn.send("PING", "VALUE")
    msg = conn.recv()

with open(os.path.join(scripts, "tests.txt"), encoding="utf-8") as f:
    text = f.read()

for lines in text.split("\n\n"):
    def build(lines):
        lines = lines.rstrip("\n")
        if not lines:
            return
        # if not lines.startswith(".tw"):
        #     return

        # @@ expected
        @test
        def test_function(conn):
            conn.handshake()

            for line in lines.split("\n"):
                line = line.replace("$(BOT)", "saxo")
                line = line.replace("$(USER)", "user")

                if line.startswith("."):
                    conn.send(":user!~user@localhost", "PRIVMSG", "#saxo", line)
                elif line == "TIMEOUT":
                    conn.nowt()
                elif line.startswith("WAIT "):
                    time.sleep(int(line.split(" ").pop().strip()))
                elif line.startswith("SAY"):
                    line = line.split(" ", 1).pop()
                    conn.send(":user!~user@localhost", "PRIVMSG", "#saxo", line)
                else:
                    if line.startswith(": "):
                        line = "user" + line
                    got = conn.recv()
                    conn.equal(got.get("command"), "PRIVMSG",
                        "Expected PRIVMSG, got %s" % got)
                    # @@ check it's to #saxo
                    got = got["parameters"][1]

                    if "<" in line:
                        patterns = []
                        for part in re.findall("<[^>]+>|[^<]+", line):
                            if part.startswith("<"):
                                patterns.append(part[1:-1])
                            else:
                                patterns.append(re.escape(part))
                        pattern = "^" + "".join(patterns) + "$"
                        msg = "Expected %r, got %r" % (pattern, got)
                        conn.match(pattern, got, msg)
                    else:
                        msg = "Expected %r, got %r" % (line, got)
                        conn.equal(line, got, msg)
                # @@ then a nowt?
    build(lines[:])

@test
def test_hang(conn):
    conn.handshake()
    conn.send(":owner!~owner@localhost", "PRIVMSG", "saxo", ".test-hang")
    time.sleep(1)

@test
def quit(conn):
    conn.send(":localhost", "NOTICE", "*", "Welcome!")
    conn.send(":owner!~owner@localhost", "PRIVMSG", "saxo", ".quit")
    time.sleep(2)

irc_regex_message = re.compile(br'(?:(:.*?) )?(.*?) (.*)')
irc_regex_address = re.compile(br':?([^!@]*)!?([^@]*)@?(.*)')
irc_regex_parameter = re.compile(br'(?:^|(?<= ))(:.*|[^ ]+)')

def parse_message(octets):
    message = {}
    octets = octets.rstrip(b'\r\n')

    message_match = irc_regex_message.match(octets)
    if not message_match:
        raise ValueError("Malformed: %r" % octets)

    prefix, command, parameters = message_match.groups()

    if prefix:
        address_match = irc_regex_address.match(prefix)
        if address_match:
            prefix = address_match.groups()

    parameters = irc_regex_parameter.findall(parameters)
    if parameters and parameters[-1].startswith(b":"):
        parameters[-1] = parameters[-1][1:]

    message["command"] = command.decode("ascii", "replace")

    message["prefix"] = {"nick": "", "user": "", "host": ""}
    if prefix:
        message["prefix"]["nick"] = prefix[0].decode("ascii", "replace")
        message["prefix"]["user"] = prefix[1].decode("ascii", "replace")
        message["prefix"]["host"] = prefix[2].decode("ascii", "replace")

    def heuristic_decode(param):
        # @@ could get these from config
        encodings = ("utf-8", "iso-8859-1", "cp1252")
        for encoding in encodings:
            try: return param.decode(encoding)
            except UnicodeDecodeError as err:
                continue
        return param.decode("utf-8", "replace")

    message["parameters_octets"] = parameters
    message["parameters"] = [heuristic_decode(p) for p in parameters]
    message["octets"] = octets
    return message

class Test(socketserver.StreamRequestHandler):
    timeout = 6

    def handle(self, *args, **kargs):
        global connections, test_counter

        connections += 1
        self.connection = connections
        self.messages = 0

        # print(dir(self.server))
        self.send(":localhost", "NOTICE", "*", "Test #%s" % self.connection)

        if self.connection in tests:
            print("Test #%s" % self.connection)
            tests[self.connection](self)

            # print(self.connection, test_counter)
            if self.connection == test_counter:
                print("Tests complete")
                self.finish()
                os._exit(0)

    def match(self, a, b, message):
        if not re.match(a, b):
            print("ERROR: Test #%s: %s" % (self.connection, message))
            self.stop()

    def equal(self, a, b, message):
        if a != b:
            print("ERROR: Test #%s: %s" % (self.connection, message))
            self.stop()

    def not_equal(self, a, b, message):
        if a == b:
            print("ERROR: Test #%s: %s" % (self.connection, message))
            self.stop()

    def stop(self):
        sys.exit(0)

    def handshake(self):
        nick = self.recv()
        self.equal(nick["command"], "NICK", "Expected NICK")

        user = self.recv()
        self.equal(user["command"], "USER", "Expected USER")

        # @@ to nick
        self.send(":localhost", "001", "saxo", "Welcome")

        join = self.recv()
        self.equal(join["command"], "JOIN", "Expected JOIN")

        who = self.recv()
        self.equal(who["command"], "WHO", "Expected WHO")

    def recv(self):
        while True:
            try: octets = self.rfile.readline()
            except socket.timeout:
                print("ERROR: Test #%s: timeout" % self.connection)
                self.stop()
                break

            # Skip blank lines
            if octets:
                break

        message = parse_message(octets)
        self.messages += 1
        message["count"] = self.messages
        return message

    def nowt(self):
        try: octets = self.rfile.readline()
        except socket.timeout:
            return True
        else:
            text = octets.decode("utf-8", "replace")
            args = (self.connection, text)
            print("ERROR: Test #%s: Expected timeout, got %r" % args)

    def send(self, *args):
        args = list(args)
        if len(args) > 1:
            args[-1] = ":" + args[-1]
        octets = " ".join(args).encode("utf-8", "replace")
        octets = octets.replace(b"\r", b"")
        octets = octets.replace(b"\n", b"")
        if len(octets) > 510:
            octets = octets[:510]
        self.wfile.write(octets + b"\r\n")
        self.wfile.flush()

    # def user
    # def channel

    def finish(self, *args, **kargs):
        socketserver.StreamRequestHandler.finish(self)

        try:
            self.request.shutdown(socket.SHUT_RDWR)
            self.request.close()
        except socket.error:
            ...

class Server(socketserver.TCPServer):
    # @@ if SystemExit, fine, otherwise raise it and os._exit(1)
    def handle_error(self, request, client_address):
        etype, evalue, etrace = sys.exc_info()
        if etype is SystemExit:
            return

        import traceback
        print("Framework Error:", etype, evalue)
        traceback.print_exc()
        os._exit(1)

def main():
    server = Server((socket.gethostname(), 61070), Test)
    server.serve_forever()

if __name__ == "__main__":
    main()
