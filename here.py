#!/usr/bin/env python3

import os

if "__path__" not in globals():
    __path__ = [os.path.dirname(__file__)]

# Cf. http://www.python.org/dev/peps/pep-0420/

# from .saxo import version
from . import saxo
print(saxo.version)
