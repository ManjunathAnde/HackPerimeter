"""GSU's Localist events API (calendar.gsu.edu/api/2/events), mapped straight to resource rows with no LLM call."""
import json
import re

MAX_SUMMARY_CHARS = 300
MAX_EVIDENCE_CHARS = 200
# Keyword dictionary for topic tags; a row gets every topic whose pattern appears in its title or description
TOPIC_KEYWORDS = {
    "health": r"health|nursing|nurse|wellness|medical|dental|clinic|flu shot|fitness|nutrition",
    "business": r"business|entrepreneur|startup|start-up|finance|marketing|accounting|robinson|launchgsu|\bmba\b|\bbba\b",
    "entrepreneurship": r"entrepreneur|startup|start-up|launchgsu|side hustle|venture",
    "tech": r"\btech|computer|\bdata\b|\bai\b|artificial intelligence|coding|cyber|software|engineering",
    "arts": r"\bart\b|\barts\b|music|theatre|theater|film|exhibit|concert|dance|gallery|chorale|ensemble",
    "education": r"education|teaching|teacher|tutoring|literacy",
    "psychology": r"psycholog|mental health|counseling",
    "career": r"career|internship|\bjobs?\b|resume|interview|employer|networking",
    "support": r"financial aid|scholarship|food pantry|basic needs|counseling|advising|tutoring|support",
}
PERIMETER_OTHER = re.compile(r"decatur|dunwoody|alpharetta|newton|panthersville", re.I)


def tag_topics(text: str) -> list[str]:
    return [t for t, pat in TOPIC_KEYWORDS.items() if re.search(pat, text, re.I)] + ["events"]


def _campus(e: dict, where: str) -> str:
    if "clarkston" in where.lower():
        return "clarkston"
    if e.get("experience") == "virtual" or where.lower() == "online":
        return "online"
    if PERIMETER_OTHER.search(where):
        return "perimeter_all"
    return "gsu_wide"


def _evidence(desc: str, title: str) -> str:
    # First sentence of the description, verbatim, so it is always a substring of the source text
    first = re.split(r"(?<=[.!?])\s", desc, maxsplit=1)[0] if desc else ""
    return (first[:MAX_EVIDENCE_CHARS] if len(first) >= 10 else title)


def parse_events(pages: list[str]) -> list[tuple[dict, str]]:
    """Returns (resource row, source text) pairs, one per unique event."""
    out, seen = [], set()
    for page in pages:
        for wrapper in json.loads(page).get("events", []):
            e = wrapper["event"]
            # The API lists one entry per instance of a recurring event
            if e["id"] in seen:
                continue
            seen.add(e["id"])
            title = (e.get("title") or "").strip()
            desc = re.sub(r"\s+", " ", e.get("description_text") or "").strip()
            where = f"{e.get('location_name') or ''} {e.get('address') or ''}".strip()
            inst = e["event_instances"][0]["event_instance"]
            text = f"{title}. {desc}"
            out.append(({
                "name": title,
                "type": "event",
                "campus": _campus(e, where),
                "audience": "all_gsu",
                "topics": tag_topics(text),
                "summary": desc[:MAX_SUMMARY_CHARS] or title,
                "how_to_start": "Register on the event page." if e.get("has_register") or e.get("ticket_url") else None,
                "location_building": e.get("location_name") or None,
                "location_room": e.get("room_number") or None,
                "event_start": inst.get("start"),
                "event_end": inst.get("end"),
                "evidence": _evidence(desc, title),
                "source_url": e.get("localist_url"),
            }, text))
    return out
