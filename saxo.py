# http://inamidst.com/saxo/
# Created by Sean B. Palmer

# Save PEP 3122!
if "." in __name__:
    from .core import *
else:
    from core import *
