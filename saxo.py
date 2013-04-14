# Copyright 2013, Sean B. Palmer
# Source: http://inamidst.com/saxo/

def event(command):
    def decorate(function):
        function.saxo_event = command
        return function
    return decorate

def script(argv):
    # Save PEP 3122!
    if "." in __name__:
        from .script import main
    else:
        from script import main
    main(argv)
