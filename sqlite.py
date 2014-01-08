# Copyright 2013-4, Sean B. Palmer
# Source: http://inamidst.com/saxo/

import re
import sqlite3

class Table(object):
    def __init__(self, connection, name):
        self.connection = connection
        self.name = name

    def __iter__(self):
        return self.rows()

    def __delitem__(self, row):
        fields = []
        for field in self.schema():
            fields.append(field[1])

        if len(row) == len(fields):
            query = "DELETE FROM %s WHERE " % self.name
            query += " AND ".join(["%s=?" % field for field in fields])
            cursor = self.connection.cursor()
            cursor.execute(query, row)
            self.connection.commit()
        else:
            raise ValueError("Wrong length: %s" % row)

    def create(self, *schema):
        cursor = self.connection.cursor()
        types = {
            None: "NULL",
            int: "INTEGER",
            float: "REAL",
            str: "TEXT",
            bytes: "BLOB"
        }
        schema = ", ".join(a + " " + types.get(b, b) for (a, b) in schema)
        query = "CREATE TABLE IF NOT EXISTS %s (%s)" % (self.name, schema)
        cursor.execute(query)
        cursor.close()

    def insert(self, row, *rows, commit=True):
        cursor = self.connection.cursor()
        size = len(row)
        args = ",".join(["?"] * size)
        query = "INSERT INTO %s VALUES(%s)" % (self.name, args)

        cursor.execute(query, tuple(row))
        for extra in rows:
            cursor.execute(query, tuple(extra))

        if commit:
            self.connection.commit()
        cursor.close()

    def rows(self, order=None):
        cursor = self.connection.cursor()
        query = "SELECT * FROM %s" % self.name

        if isinstance(order, str):
            if order.isalpha():
                query += " ORDER BY %s" % order

        cursor.execute(query)
        while True:
            result = cursor.fetchone()
            if result is None:
                break
            yield result
        cursor.close()

    def schema(self):
        cursor = self.connection.cursor()
        query = "PRAGMA table_info(%s)" % self.name
        cursor.execute(query)
        while True:
            result = cursor.fetchone()
            if result is None:
                break
            yield result
        cursor.close()

class Database(object):
    def __init__(self, path):
        self.path = path
        self.connection = sqlite3.connect(path)

        def regexp(pattern, text):
            return re.search(pattern, text) is not None
        self.connection.create_function("REGEXP", 2, regexp)

    def __iter__(self):
        raise NotImplemented

    def __delitem__(self, key):
        if key in self:
            query = "DROP TABLE %s" % key
            cursor = self.connection.cursor()
            cursor.execute(query)
            cursor.close()

    def __contains__(self, key):
        cursor = self.connection.cursor()
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        cursor.execute(query, (key,))
        result = cursor.fetchone() is not None
        cursor.close()
        return result

    def __getitem__(self, key):
        return Table(self.connection, key)

    def __enter__(self, *args, **kargs):
        return self

    def __exit__(self, *args, **kargs):
        # TODO: Check for changes to commit?
        # self.connection.commit()
        self.connection.close()

    def commit(self):
        self.connection.commit()

    def execute(self, text, *args):
        cursor = self.connection.cursor()
        if not args:
            cursor.execute(text)
        else:
            cursor.execute(text, args)
        return cursor

    def query(self, text, *args):
        cursor = self.execute(text, *args)
        # Duplicate rows are sometimes given,
        # even when sqlite3 was compiled thread-safe
        previous = None
        while True:
            result = cursor.fetchone()
            if result is None:
                break
            if result == previous:
                continue
            yield result
            previous = result
        cursor.close()

def test():
    import os

    filename = "/tmp/saxo-test.sqlite3"
    if os.path.isfile(filename):
        os.remove(filename)

    with Database(filename) as db:
        assert "example" not in db
        db["example"].create(
            ("name", str),
            ("size", int))

        assert "example" in db
        db["example"].insert(
            ("pqr", 5),
            ("abc", 10))

        print(list(db["example"]))
        assert list(db["example"].rows(order="name")) == [('abc', 10), ('pqr', 5)]
        assert list(db["example"].rows(order="size")) == [('pqr', 5), ('abc', 10)]
        print(list(db["example"].schema()))

        del db["example"][("pqr", 5)]
        print(list(db["example"]))

    os.remove(filename)

if __name__ == "__main__":
    test()
