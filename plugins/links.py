# http://inamidst.com/saxo/
# Created by Sean B. Palmer

import re
import saxo

regex_link = re.compile(r"(http[s]?://[^<> \"\x01]+)[,.]?")

@saxo.event("PRIVMSG")
def link(irc):
    search = regex_link.search(irc.text)
    if search:
        if irc.sender.startswith("#"):
            irc.client("link", irc.sender, search.group(1))
