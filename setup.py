# Copyright 2013-4, Sean B. Palmer
# Source: http://inamidst.com/saxo/

# python3 setup.py sdist --formats=bztar
# python3 setup.py bdist_wheel

import os.path
import sys

def error(*messages):
    for message in messages:
        print(message, file=sys.stderr)
    sys.exit(1)

try: from setuptools import setup
except ImportError as err:
    if "bdist_wheel" in sys.argv:
        error("Option bdist_wheel requires setuptools, which can't be found")
    from distutils.core import setup

try: import sqlite3
except ImportError:
    error("Error: sqlite3 is not installed",
          "Please build Python against the sqlite libraries")
else:
    if not sqlite3.threadsafety:
        error("Error: Your sqlite3 is not thread-safe")

# Do wheels invoke setup.py?
if sys.version_info < (3, 3):
    error("Error: Requires Python 3.3 or later")

def update_version():
    if os.path.isfile("version"):
        with open("version", "r", encoding="ascii") as f:
            version = f.read().rstrip("\r\n")

        if os.path.isdir(".git") and ("sdist" in sys.argv):
            major, minor, serial = [int(n) for n in version.split(".")]
            version = "%s.%s.%s" % (major, minor, serial + 1)

            with open("version", "w", encoding="ascii") as f:
                f.write(version)
    else:
        error("Error: No saxo version file found")

    return version

# http://stackoverflow.com/questions/4384796
# http://packages.python.org/distribute/

if __name__ == "__main__":
    README = "https://github.com/sbp/saxo/blob/master/README.md"

    setup(
        name="saxo",
        version=update_version(),
        author="Sean B. Palmer",
        url="http://inamidst.com/saxo/",
        description="Quick and flexible irc bot, extensible in any language",
        long_description="Documented in `@sbp/saxo/README.md <%s>`_" % README,
        packages=["saxo"],
        package_dir={"saxo": "."},
        package_data={"saxo": [
            "README.md", "commands/*", "plugins/*", "test/*", "version"
        ]},
        scripts=["saxo"],
        platforms="Linux and OS X",
        classifiers=[
            "Operating System :: MacOS :: MacOS X",
            "Operating System :: POSIX",
            "Programming Language :: Python :: 3"
        ]
    )
