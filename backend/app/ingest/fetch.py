"""HTTP fetch limited to allowlisted domains, rate limited, with a small retry for bot challenges."""
import time
from urllib.parse import urlparse

import httpx
import yaml

from app import config

_SOURCES_CFG = yaml.safe_load((config.CONFIG_DIR / "sources.yaml").read_text())
ALLOW_DOMAINS = _SOURCES_CFG["allow_domains"]
MIN_INTERVAL = 1.0 / _SOURCES_CFG.get("rate_limit_per_sec", 1)
RETRIES = 3
RETRY_WAIT_SEC = 5
_last_request = 0.0


class FetchError(Exception):
    pass


def is_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in ALLOW_DOMAINS)


def _wait_for_rate_limit() -> None:
    global _last_request
    delay = MIN_INTERVAL - (time.monotonic() - _last_request)
    if delay > 0:
        time.sleep(delay)
    _last_request = time.monotonic()


def fetch(url: str) -> tuple[str, str]:
    """Returns (body text, final url). GSU sites sometimes answer 403/202 bot challenges; we retry, never bypass."""
    if not is_allowed(url):
        raise FetchError(f"domain not allowlisted: {url}")
    last = ""
    for attempt in range(1, RETRIES + 1):
        _wait_for_rate_limit()
        try:
            resp = httpx.get(url, headers={"User-Agent": config.HTTP_USER_AGENT}, follow_redirects=True, timeout=25)
        except httpx.HTTPError as e:
            last = f"{type(e).__name__}: {e}"
        else:
            final = str(resp.url)
            if not is_allowed(final):
                raise FetchError(f"redirected off allowlist: {final}")
            if resp.status_code == 200 and resp.text:
                return resp.text, final
            last = f"HTTP {resp.status_code} ({len(resp.content)} bytes)"
        if attempt < RETRIES:
            time.sleep(RETRY_WAIT_SEC)
    raise FetchError(f"{url}: {last} after {RETRIES} tries")
