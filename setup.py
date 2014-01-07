# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

# python3 setup.py sdist --formats=bztar

import os.path
import sys

try: from setuptools import setup
except ImportError as err:
    if "bdist_wheel" in sys.argv:
        raise err
    from distutils.core import setup

try: import sqlite3
except ImportError:
    print("Error: sqlite3 is not installed", file=sys.stderr)
    print("Please build Python against the sqlite libraries", file=sys.stderr)
    sys.exit(1)
else:
    if not sqlite3.threadsafety:
        print("Error: Your sqlite3 is not thread-safe", file=sys.stderr)
        sys.exit(1)

if sys.version_info < (3, 3):
    print("Error: Requires Python 3.3 or later", file=sys.stderr)
    sys.exit(1)

def update_version():
    if os.path.isfile("saxo.py"):
        offset = 81
        with open("saxo.py", "r+", encoding="utf-8") as f:
            f.seek(offset)
            version = f.read(7)

            if os.path.isdir(".git") and ("sdist" in sys.argv):
                patch = int(version[-3:]) + 1
                if patch > 999:
                   raise ValueError("Update major/minor version")
                version = version[:-3] + "%03i" % patch

                f.seek(offset)
                f.write(version)
    else:
        print("Unable to find saxo.py script: refusing to install")
        sys.exit(1)

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
            "README.md", "commands/*", "plugins/*", "test/*"
        ]},
        scripts=["saxo"],
        platforms="Linux and OS X",
        classifiers=[
            "Operating System :: MacOS :: MacOS X",
            "Operating System :: POSIX",
            "Programming Language :: Python :: 3"
        ]
    )
