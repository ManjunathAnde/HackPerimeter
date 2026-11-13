"""Before the pitch: clear eni_cal rows and all alerts so "Run now" on eni_cal recreates rows and fires an alert."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db  # noqa: E402

DEMO_SOURCE = "eni_cal"

db.init_db()
conn = db.connect()
with conn:
    rows = conn.execute("DELETE FROM resources WHERE source_id = ?", (DEMO_SOURCE,)).rowcount
    alerts = conn.execute("DELETE FROM alerts").rowcount
    # Without this the content-hash check sees an unchanged feed and skips re-extraction
    conn.execute("UPDATE sources SET content_hash = NULL WHERE id = ?", (DEMO_SOURCE,))
print(f"demo_reset: removed {rows} {DEMO_SOURCE} rows, {alerts} alerts; {DEMO_SOURCE} hash cleared")
