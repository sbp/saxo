# Copyright 2013-4, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import os.path
import random
import sys

# Save PEP 3122!
if "." in __name__:
    from . import common
    from .saxo import path as saxo_path
else:
    import common
    from saxo import path as saxo_path

DEFAULT_CONFIG = """\
# See docs/config.md for more options

[server]
    host = irc.freenode.net
    port = 6667

[client]
    nick = saxo%05i
    channels = ##saxo #test
    prefix = .
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

def default(base=None):
    if base is None:
        base = os.path.expanduser("~/.saxo")

    if os.path.isdir(base):
        common.error("the directory `%s` already exists" % base,
            E_DIRECTORY_EXISTS)

    try: os.makedirs(base)
    except Exception as err:
        common.error("could not create the directory `%s`" % base,
            E_UNMAKEABLE_DIRECTORY, err)

    config = os.path.join(base, "config")
    try:
        with open(config, "w", encoding="ascii") as f:
            # Generates a random bot name, from saxo00000 to saxo99999 inclusive
            f.write(DEFAULT_CONFIG % random.randrange(0, 100000))
    except Exception as err:
        common.error("could not write the config file `%s`" % config,
            E_UNWRITEABLE_CONFIG, err)

    plugins = os.path.join(base, "plugins")
    os.mkdir(plugins)

    commands = os.path.join(base, "commands")
    os.mkdir(commands)

    common.populate(saxo_path, base)

    print("Created %s" % config)
    print("Modify this file with your own settings, and then run:")
    print("")
    if base:
        print("    %s start %s" % (sys.argv[0], base))
    else:
        print("    %s start" % sys.argv[0])

    return True
