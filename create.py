# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import os.path
import random
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

DEFAULT_CONFIG = """\
# See TODO for more options

[server]
    host = irc.freenode.net
    port = 6667
    ssl = False

[client]
    nick = saxo%05i
    channels = ##saxo #test
"""

E_DIRECTORY_EXISTS = """
You tried to make a directory that already exists. This is usually caused by
saxo already existing through a previous creation command. It may also be
caused by a path conflict, for example if you thought that you needed to
manually create the saxo directory beforehand.

This script won't write new material into any existing directories in case of
data corruption.
"""

E_UNMAKEABLE_DIRECTORY = """
The attempt to make this directory recursively, creating any necessary parent
directories in the process, failed. Check permissions on all parent directories
to make sure that we can write here. Also make sure that the parent path is a
directory.
"""

E_UNWRITEABLE_CONFIG = """
The saxo config file could not be written. Check that it exists, that it's a
regular file, and that you have adequate permissions to write on all parent
directories.
"""

def default(directory=None):
    if directory is None:
        directory = os.path.expanduser("~/.saxo")

    if os.path.isdir(directory):
        error("the directory `%s` already exists" % directory,
            E_DIRECTORY_EXISTS)

    try: os.makedirs(directory)
    except Exception as err:
        error("could not create the directory `%s`" % directory,
            E_UNMAKEABLE_DIRECTORY, err)

    config = os.path.join(directory, "config")
    try:
        with open(config, "w", encoding="ascii") as f:
            # Generates a random bot name, from saxo00000 to saxo99999 inclusive
            f.write(DEFAULT_CONFIG % random.randrange(0, 100000))
    except Exception as err:
        error("could not write the config file `%s`" % config,
            E_UNWRITEABLE_CONFIG, err)

    plugins = os.path.join(directory, "plugins")
    os.mkdir(plugins)

    print("Created %s" % config)
    print("Modify this file with your own settings, and then run:")
    print("")
    print("    %s start" % sys.argv[0])

    return True
