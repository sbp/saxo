# Copyright 2012-4, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import os.path
import saxo
import unicodedata

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

def populate_table_python(db):
    for codepoint in range(1, 0x10000):
        hexcode = "%04X" % codepoint

        # Skip surrogates
        if hexcode in surrogates:
            character = ""
        else:
            character = chr(codepoint)

        try: category = unicodedata.category(character)
        except TypeError:
            continue

        try: character.encode("utf-8")
        except UnicodeEncodeError:
            continue

        if category.startswith("M"):
            # TODO: Just Mn?
            display = "\u25CC" + character
        elif category.startswith("C") and not category.endswith("o"):
            # Co is Private_Use, allow those
            if 0 <= codepoint <= 0x1F:
                display = chr(codepoint + 0x2400)
            else:
                display = "<%s>" % category
        else:
            display = character

        try: name = unicodedata.name(character)
        except ValueError:
            name = "<control>"

        current = name[:]
        ancient = ""

        db["saxo_unicode"].insert((hexcode, codepoint, name, current,
            ancient, category, character, display), commit=False)

    db.commit()

def populate_table_web(db):
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

@saxo.setup
def setup(irc):
    path = os.path.join(irc.base, "database.sqlite3")
    with saxo.database(path) as db:
        if "saxo_unicode" not in db:
            create_table(db)
            populate_table_python(db)

@saxo.command("update-unicode-data")
def update_unicode_data(irc):
    if "owner" in irc.config:
        if irc.prefix == irc.config["owner"]:
            path = os.path.join(irc.base, "database.sqlite3")
            with saxo.database(path) as db:
                if "saxo_unicode" in db:
                    delete_table(db)
                create_table(db)
                irc.say("Downloading UnicodeData.txt from unicode.org...")
                populate_table_web(db)
                irc.say("Updated saxo_unicode in database.sqlite3")

@saxo.command("remove-unicode-data")
def remove_unicode_data(irc):
    if "owner" in irc.config:
        if irc.prefix == irc.config["owner"]:
            path = os.path.join(irc.base, "database.sqlite3")
            with saxo.database(path) as db:
                if "saxo_unicode" in db:
                    delete_table(db)
                    irc.say("Removed saxo_unicode from database.sqlite3")
                else:
                    irc.say("No saxo_unicode table in database.sqlite3")
