"""Child: commit N rows with production pragmas, then DIE HARD without closing."""
import os
import sqlite3
import sys

db, ap, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
c = sqlite3.connect(db)
c.execute("PRAGMA journal_mode=WAL")
c.execute("PRAGMA busy_timeout=5000")
c.execute(f"PRAGMA wal_autocheckpoint={ap}")
c.execute("PRAGMA synchronous=NORMAL")
c.execute("CREATE TABLE IF NOT EXISTS durability (k INTEGER PRIMARY KEY, v TEXT)")
c.commit()
for i in range(n):
    c.execute("INSERT OR REPLACE INTO durability (k,v) VALUES (?,?)", (i, "payload"*20))
    c.commit()                      # COMMITTED. No checkpoint forced. No close.
print(f"child committed {n} rows at autocheckpoint={ap}", flush=True)
os._exit(9)                         # hard kill: no close, no atexit, no checkpoint
