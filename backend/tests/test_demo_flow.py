"""Demo steps 1-6 through the API, against the real KB and live LLMs. Run after scripts/demo_reset.py."""
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app import config, demo_cache, llm  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def card_names(data: dict) -> list[str]:
    return [m["resource"]["name"] for m in data["matches"]]


def assert_sourced(resource: dict) -> None:
    assert resource["source_url"].startswith("https://"), resource["id"]
    assert resource["fetched_at"], resource["id"]


def test_step1_profile():
    p = client.get("/api/profile").json()
    assert (p["name"], p["campus"], p["pathway_id"], p["credits"]) == ("Jordan", "clarkston", "business_admin", 30)
    assert {"business", "entrepreneurship"} <= set(p["topics"])


@pytest.fixture(scope="module")
def step2():
    r = client.post("/api/chat", json={"message": demo_cache.STEP2, "history": []})
    assert r.status_code == 200, r.text
    return r.json()


def test_step2_cards(step2):
    names = card_names(step2)
    assert any("LaunchGSU" in n for n in names), names
    assert any("Entrepreneurship and Innovation Institute" in n for n in names), names
    assert any(m["resource"]["type"] == "event" for m in step2["matches"]), names
    for m in step2["matches"]:
        assert_sourced(m["resource"])
        assert m["why"] and m["first_step"]


def test_step2_trace_and_verification(step2):
    steps = {t["step"] for t in step2["trace"]}
    assert {"plan", "search", "answer", "verify"} <= steps, steps
    assert steps & {"refetch", "freshness"}, steps
    assert step2["verification"]["checker"] in {"gemini", "groq"}


def test_step3_email_draft():
    r = client.post("/api/draft-email", json={"resource_id": "launchgsu_dept:launchgsu"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["subject"] and "Jordan" in d["body"]
    assert d["to"] is None or "@" in d["to"]
    assert d["contact_url"].startswith("https://")


def test_step4_clarkston_question():
    r = client.post("/api/chat", json={"message": demo_cache.STEP4, "history": []})
    assert r.status_code == 200, r.text
    names = card_names(r.json())
    # Narrated as "Perimeter and Clarkston business resources": either anchor card is acceptable
    assert any("Perimeter Business Club" in n or "Side Hustle Ideation Workshop" in n for n in names), names
    for m in r.json()["matches"]:
        assert_sourced(m["resource"])


def test_step5_roadmaps():
    ids = [p["id"] for p in client.get("/api/pathways").json()]
    assert ids == ["business_admin", "startup"]
    for pid in ids:
        rm = client.get(f"/api/pathways/{pid}/roadmap").json()
        assert len(rm["steps"]) >= 5, (pid, len(rm["steps"]))
        for step in rm["steps"]:
            assert step["resources"], step["title"]
            assert_sourced(step["resources"][0])
    stats = client.get("/api/stats").json()
    assert stats["total"] >= 25 and stats["by_type"]


def test_step6_reset_then_run_now_creates_alert():
    out = subprocess.run([sys.executable, str(BACKEND / "scripts" / "demo_reset.py")], capture_output=True, text=True, check=True)
    assert "demo_reset: removed" in out.stdout
    assert client.get("/api/alerts?unread=1").json() == []
    r = client.post("/api/sources/eni_cal/run")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["run"]["error"] is None and body["run"]["rows_new"] >= 1
    assert body["alerts_created"] >= 1
    unread = client.get("/api/alerts?unread=1").json()
    assert unread and all("ENI" in a["message"] for a in unread)
    src = next(s for s in client.get("/api/sources").json() if s["id"] == "eni_cal")
    assert src["rows_total"] >= 1 and src["last_status"] == "ok"


def test_cache_fallback_when_both_llms_fail(monkeypatch):
    def down(prompt):
        raise RuntimeError("simulated outage")

    monkeypatch.setattr(llm, "PROVIDERS", [("gemini", down), ("groq", down)])
    monkeypatch.setattr(config, "DEMO_FALLBACK", True)
    r = client.post("/api/chat", json={"message": demo_cache.STEP2, "history": []})
    assert r.status_code == 200, r.text
    assert r.json()["trace"][0]["step"] == "cache"
    assert any("LaunchGSU" in n for n in card_names(r.json()))
