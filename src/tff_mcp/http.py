"""HTTP layer for tff_mcp.

tff.org (Turkish Football Federation) serves its league pages fully
server-rendered — standings (``s-table``), fixtures
(``fiksturListesiTable``), top scorers (``rptGolKralligi`` repeater)
and match details (pageID=29&macId=...) — with plain HTTP 200, no
login, no API key, no session cookies (verified live 2026-11-09).
The site is legacy ASP.NET and answers in windows-1254, so bodies
are decoded explicitly instead of trusting the transport's guess.
Transport still uses curl-cffi chrome120 impersonation, the proven
pattern of the other Turkey-factory servers. Requests are kept
gentle (one at a time, ~0.8s apart) and read-only. GET only.
"""
from __future__ import annotations

import time
from urllib.parse import quote

from curl_cffi import requests as _r

BASE = "https://www.tff.org"
TIMEOUT = 30.0
MIN_INTERVAL = 0.8  # seconds between requests — be polite

_HEADERS = {
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

_last_fetch = 0.0


class TffError(RuntimeError):
    pass


_PROFILES = ("chrome120", "chrome131", "safari17_0")
_MAX_ATTEMPTS = 2  # one retry with the next profile
_RETRY_BACKOFF = 1.0  # seconds between attempts
_profile_idx = 0  # sticky: profile that last succeeded


def _request(url: str, headers: dict, timeout: float = TIMEOUT):
    """GET with fingerprint rotation.

    Starts at the sticky profile (chrome120 on a fresh process), retries
    once with the next profile on HTTP 403/429 or a transport error, then
    returns the last response (so the caller raises the specific 403/429
    error) or raises a network error if every attempt failed at the
    transport. Added 2026-11-10 (fleet audit fix).
    """
    global _profile_idx
    last_exc: Exception | None = None
    for k in range(_MAX_ATTEMPTS):
        profile = _PROFILES[(_profile_idx + k) % len(_PROFILES)]
        try:
            resp = _r.get(url, impersonate=profile, headers=headers, timeout=timeout)
        except Exception as e:
            last_exc = e
            if k + 1 < _MAX_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF)
                continue
            raise TffError(f"network error fetching {url}: {e}") from e
        if resp.status_code in (403, 429):
            if k + 1 < _MAX_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF)
                continue
            return resp
        _profile_idx = (_profile_idx + k) % len(_PROFILES)
        return resp
    raise TffError(f"network error fetching {url}: {last_exc}") from last_exc


def _get(url: str) -> str:
    global _last_fetch
    wait = MIN_INTERVAL - (time.monotonic() - _last_fetch)
    if wait > 0:
        time.sleep(wait)
    try:
        resp = _request(url, _HEADERS)
    except TffError:
        raise
    except Exception as e:
        raise TffError(f"network error fetching {url}: {e}") from e
    finally:
        _last_fetch = time.monotonic()
    if resp.status_code == 403:
        raise TffError(
            "tff.org refused the request (HTTP 403, bot wall) — try again later"
        )
    if resp.status_code == 429:
        raise TffError(
            "tff.org rate-limited the request (HTTP 429) — try again later"
        )
    if resp.status_code in (404, 410):
        raise TffError(
            f"page not found (HTTP {resp.status_code}): {url} — check the "
            "league / match id"
        )
    if resp.status_code != 200:
        raise TffError(f"unexpected HTTP {resp.status_code} fetching {url}")
    # Legacy ASP.NET site: windows-1254, declared in the content-type.
    # Decode explicitly — the transport's charset guess is unreliable.
    try:
        return resp.content.decode("windows-1254")
    except (UnicodeDecodeError, LookupError):
        return resp.text


def fetch_league_html(page_id: str, grup_id: str | None = None) -> str:
    """League standings+fixtures page: /default.aspx?pageID=<id>
    (optionally &grupID=<id> for one group of a multi-group league)."""
    url = f"{BASE}/default.aspx?pageID={quote(page_id)}"
    if grup_id:
        url += f"&grupID={quote(grup_id)}"
    return _get(url)


def fetch_match_html(mac_id: str) -> str:
    """Match detail page: /Default.aspx?pageID=29&macId=<id>."""
    return _get(f"{BASE}/Default.aspx?pageID=29&macId={quote(str(mac_id))}")


def fetch_scorers_html(page_id: str) -> str:
    """Top-scorers page: /default.aspx?pageID=<id> (821/822/823/824)."""
    return _get(f"{BASE}/default.aspx?pageID={quote(page_id)}")


def fetch_home_html() -> str:
    """Homepage HTML (used by health_check)."""
    return _get(f"{BASE}/")


def health_check() -> dict:
    """One polite probe of the source site.

    Returns {"status": "ok"|"blocked"|"error", "http_status": int|None,
    "url": ..., "detail": ...}. Used by the `tff_health` tool
    and the daily smoke CI. Added 2026-11-10 (fleet audit fix).
    """
    url = "https://www.tff.org/"
    try:
        fetch_home_html()
    except TffError as e:
        msg = str(e)
        if "403" in msg:
            return {"status": "blocked", "http_status": 403, "url": url, "detail": msg}
        if "429" in msg:
            return {"status": "blocked", "http_status": 429, "url": url, "detail": msg}
        return {"status": "error", "http_status": None, "url": url, "detail": msg}
    return {"status": "ok", "http_status": 200, "url": url}
