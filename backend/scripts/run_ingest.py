"""Run ingestion for every enabled source (or the ids given) and print per-source results."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db  # noqa: E402
from app.agents import ingestion  # noqa: E402

db.init_db()
ids = sys.argv[1:] or [s["id"] for s in ingestion.load_sources()]
for sid in ids:
    run = ingestion.run_source(sid)
    print(f"{sid}: new={run['rows_new']} changed={run['rows_changed']} unchanged={run['rows_unchanged']} "
          f"dropped={run['rows_dropped']} evidence_verified={run['evidence_verified']} error={run['error']}")

conn = db.connect()
print("\nrows per source:")
for r in conn.execute("SELECT source_id, COUNT(*) n FROM resources GROUP BY source_id ORDER BY source_id"):
    print(f"  {r['source_id']}: {r['n']}")
print("ingestion_runs logged:", conn.execute("SELECT COUNT(*) FROM ingestion_runs").fetchone()[0])
