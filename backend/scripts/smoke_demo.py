"""Run demo steps 2 and 4 against the running API, check them, and save the answers as the demo fallback cache."""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import demo_cache  # noqa: E402

API = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api"
CHECKS = {
    demo_cache.STEP2: ["LaunchGSU"],
    demo_cache.STEP4: ["Perimeter Business Club"],
}

responses, failed = {}, False
for message, must_include in CHECKS.items():
    r = httpx.post(f"{API}/chat", json={"message": message, "history": []}, timeout=180)
    r.raise_for_status()
    data = r.json()
    names = [m["resource"]["name"] for m in data["matches"]]
    missing = [n for n in must_include if not any(n.lower() in x.lower() for x in names)]
    unsourced = [m["resource"]["name"] for m in data["matches"] if not m["resource"].get("source_url")]
    ok = data["answer"] and names and not missing and not unsourced
    failed |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {message!r}\n  cards: {names}\n  missing: {missing} unsourced: {unsourced}")
    responses[message] = data

if failed:
    sys.exit("smoke_demo: FAILED, cache not written")
demo_cache.save(responses)
print(f"smoke_demo: PASSED, wrote {demo_cache.CACHE_PATH}")
