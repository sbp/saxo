# Copyright 2012-3, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import os.path
import saxo

surrogates = {"D800", "DB7F", "DB80", "DBFF", "DC00", "DFFF"}

def create_table(db):
    db["saxo_unicode"].create(
        ("hexcode", str),
        ("codepoint", int),
        ("name", str),
        ("current", str),
        ("ancient", str),
        ("category", str),
        ("character", str),
        ("display", str))

def populate_table(db):
    url = "http://www.unicode.org/Public/UNIDATA/UnicodeData.txt"
    page = saxo.request(url)

    for line in page["text"].splitlines():
        a, b, c, d, e, f, g, h, i, j, k, l, m, n, o = line.split(";")

        hexcode = a
        category = c
        codepoint = int(a, 16)

        # Skip surrogates
        if a in surrogates:
            character = ""
        else:
            character = chr(codepoint)

        if c.startswith("M"):
            # TODO: Just Mn?
            display = "\u25CC" + character
        elif c.startswith("C") and not c.endswith("o"):
            # Co is Private_Use, allow those
            if 0 <= codepoint <= 0x1F:
                display = chr(codepoint + 0x2400)
            else:
                display = "<%s>" % c
        else:
            display = character

        if b != "<control>":
            name = b
        else:
            name = k or b
        current = b
        ancient = k

        db["saxo_unicode"].insert((hexcode, codepoint, name, current,
            ancient, category, character, display), commit=False)

    db.commit()

def delete_table(db):
    del db["saxo_unicode"]

@saxo.command("update-unicode-data")
def update_unicode_database(irc):
    if "owner" in irc.client:
        if irc.prefix == irc.client["owner"]:
            path = os.path.join(irc.base, "database.sqlite3")
            with saxo.db(path) as db:
                if "saxo_unicode" in db:
                    delete_table(db)
                create_table(db)
                irc.say("Downloading UnicodeData.txt from unicode.org...")
                populate_table(db)
                irc.say("Updated saxo_unicode in database.sqlite3")
