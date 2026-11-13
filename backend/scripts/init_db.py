import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, db  # noqa: E402

db.init_db()
conn = db.connect()
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table') ORDER BY name")]
print("db:", config.DATABASE_PATH)
print("tables:", tables)
print("profile:", db.get_profile(conn))
