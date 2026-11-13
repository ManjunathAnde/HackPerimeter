from datetime import timezone
from email.utils import parsedate_to_datetime

import feedparser

from app.ingest.parse_html import clean_text


def _iso(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None


def parse_items(xml: str) -> list[dict]:
    """One dict per feed item: the text the LLM reads plus fields code sets directly."""
    items = []
    for e in feedparser.parse(xml).entries:
        title = e.get("title", "").strip()
        description = clean_text(e.get("description", ""))
        items.append({
            "text": f"{title}. {description}",
            "link": e.get("link"),
            # Localist puts the event start in pubDate
            "event_start": _iso(e.get("published")),
        })
    return items
