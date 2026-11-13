"""GSU's Localist events API (calendar.gsu.edu/api/2/events): filter to Clarkston or business-related events."""
import json
import re

MAX_DESC_CHARS = 600


def parse_events(pages: list[str], keywords: list[str]) -> list[dict]:
    kw = re.compile("|".join(re.escape(k) for k in keywords), re.I)
    events, seen = [], set()
    for page in pages:
        for wrapper in json.loads(page).get("events", []):
            e = wrapper["event"]
            # The API lists one entry per instance of a recurring event
            if e["id"] in seen:
                continue
            seen.add(e["id"])
            where = f"{e.get('location_name') or ''} {e.get('address') or ''}".strip()
            depts = " ".join(d.get("name", "") for d in e.get("departments") or [])
            desc = re.sub(r"\s+", " ", e.get("description_text") or "").strip()[:MAX_DESC_CHARS]
            at_clarkston = "clarkston" in where.lower()
            if not (at_clarkston or kw.search(f"{e.get('title', '')} {desc} {depts}")):
                continue
            inst = e["event_instances"][0]["event_instance"]
            events.append({
                "text": f"{e['title']}. Location: {where or 'not listed'}. {desc}",
                "link": e.get("localist_url"),
                "event_start": inst.get("start"),
                "event_end": inst.get("end"),
                "location": e.get("location_name") or None,
                "clarkston": at_clarkston,
            })
    return events
