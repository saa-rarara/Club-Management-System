"""Testing-only stand-in for mysql.connector, backed by SQLite. Used by dev_tests/run_tests.py only."""
"""Minimal stand-in for mysql.connector backed by SQLite (testing only)."""
import os, re, sqlite3, datetime as _dt

class Error(Exception): pass
class IntegrityError(Error): pass

sqlite3.register_adapter(_dt.datetime, lambda v: v.strftime("%Y-%m-%d %H:%M:%S"))
sqlite3.register_adapter(_dt.date, lambda v: v.isoformat())
sqlite3.register_adapter(bool, int)

QUERY_LOG = []

def translate(q):
    q = q.replace("%s", "?")
    q = q.replace("NOW()", "CURRENT_TIMESTAMP")
    q = re.sub(r"CAST\((.*?) AS CHAR\)", r"CAST(\1 AS TEXT)", q)
    if "ON DUPLICATE KEY UPDATE" in q:
        q = q.replace("ON DUPLICATE KEY UPDATE", "ON CONFLICT DO UPDATE SET")
        q = re.sub(r"VALUES\((\w+)\)", r"excluded.\1", q)
    return q

class Cursor:
    def __init__(self, conn, dictionary):
        self._c = conn.cursor(); self._dict = dictionary
    def execute(self, q, params=()):
        tq = translate(q); QUERY_LOG.append(tq)
        try:
            self._c.execute(tq, tuple(params) if params else ())
        except sqlite3.IntegrityError as e: raise IntegrityError(str(e))
        except sqlite3.Error as e: raise Error(f"{e} :: {tq}")
    def _row(self, r):
        if r is None: return None
        if self._dict: return {d[0]: v for d, v in zip(self._c.description, r)}
        return r
    def fetchone(self): return self._row(self._c.fetchone())
    def fetchall(self): return [self._row(r) for r in self._c.fetchall()]
    @property
    def rowcount(self): return self._c.rowcount
    @property
    def lastrowid(self): return self._c.lastrowid
    def close(self): self._c.close()

class Connection:
    def __init__(self):
        self._conn = sqlite3.connect(os.environ["FAKE_DB_PATH"])
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._open = True
    def cursor(self, dictionary=False): return Cursor(self._conn, dictionary)
    def commit(self): self._conn.commit()
    def rollback(self): self._conn.rollback()
    def start_transaction(self): pass
    def is_connected(self): return self._open
    def close(self): self._conn.close(); self._open = False

def connect(**kw):
    if kw.get("password") == "wrong": raise Error("Access denied")
    return Connection()
