import sqlite3
import pickle
from collections.abc import MutableMapping


# PersistKV = persist.persistKV('/home/jacob/ebay/price.sqlite3')
# priced_time = PersistKV('priced_time')

def persistKV(dbfile):
    class PersistKV(MutableMapping):
        con = sqlite3.connect(dbfile, timeout=10.0, isolation_level=None)

        def __init__(self, table='kv'):
            self.table = table
            with self.con as con:
                con.execute(f"CREATE TABLE IF NOT EXISTS {table} (k text PRIMARY KEY, v text)")

        def __enter__(self):
            self.con.execute("BEGIN EXCLUSIVE")
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            if exc_type is None:
                self.con.commit()
            else:
                print("WARNING: transaction rollback")
                self.con.rollback()

        def __setitem__(self, k, v):
            with self.con as con:
                con.execute(f"REPLACE INTO {self.table} (k, v) VALUES (?, ?)", (pickle.dumps(k), pickle.dumps(v)))

        def __getitem__(self, k):
            row = self.con.execute(f"SELECT v FROM {self.table} WHERE k = ?", (pickle.dumps(k),)).fetchone()
            if not row:
                raise KeyError(k)
            return pickle.loads(row[0])

        def __delitem__(self, k):
            self.con.execute(f"DELETE FROM {self.table} WHERE k = ?", (pickle.dumps(k),))

        def __iter__(self):
            return (pickle.loads(row[0]) for row in self.con.execute(f"SELECT k FROM {self.table}").fetchall())

        def __len__(self):
            return self.con.execute(f"SELECT COUNT(*) FROM {self.table}").fetchone()[0]

        def __repr__(self):
            return dict(self).__repr__()

        def __del__(self):
            self.con.commit()

    return PersistKV
