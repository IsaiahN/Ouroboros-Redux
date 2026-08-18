"""THE DURABILITY TEST. Does a COMMITTED transaction survive a hard kill WITHOUT a
checkpoint? This gates both wal_autocheckpoint=100 and FIX #16's per-statement commit,
because both were chosen on the belief that it does not."""
import sqlite3, subprocess, os, sys, shutil
PY, SP, N = sys.executable, os.path.dirname(os.path.abspath(__file__)), 500
for ap in (100, 1000, 10000):
    db = os.path.join(SP, f"dur_{ap}.db")
    for ext in ("", "-wal", "-shm"):
        if os.path.exists(db + ext): os.remove(db + ext)
    r = subprocess.run([PY, os.path.join(SP, "writer.py"), db, str(ap), str(N)],
                       capture_output=True, text=True, check=False)
    killed = (r.returncode == 9)
    wal = os.path.getsize(db + "-wal") if os.path.exists(db + "-wal") else 0
    c = sqlite3.connect(db)              # reopen: SQLite replays the WAL here
    got = c.execute("SELECT COUNT(*) FROM durability").fetchone()[0]
    c.close()
    print(f"  autocheckpoint={ap:<6} child hard-killed={killed}  WAL left={wal:>9,} B  "
          f"rows recovered = {got}/{N}   {'ALL SURVIVED' if got==N else '** LOSS **'}")
print("\nIf all rows survive at every setting, CHECKPOINT FREQUENCY DOES NOT DECIDE")
print("SURVIVAL OF COMMITTED DATA -- it decides how much WAL is replayed on reopen.")
