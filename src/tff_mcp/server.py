"""MCP server: unofficial read-only access to tff.org (Turkish
Football Federation)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import football as _F
from . import http as _http

mcp = FastMCP("tff-mcp")

INSTRUCTIONS = """\
Unofficial read-only MCP server for tff.org, the Turkish Football
Federation (TFF) — league standings (puan cetveli), fixtures
(fikstür), match details, and top scorers (gol krallığı) for 18
Turkish leagues, from the Süper Lig down to the youth development
leagues. Data comes from the site's server-rendered pages — no
login, no API key. Standings and fixtures live on each league's
page (/default.aspx?pageID=<id>); multi-group leagues (Nesine 2.
Lig, Nesine 3. Lig, BAL, women's and youth leagues) take a group
(by index, group id, or name — "Kırmızı", "Beyaz", "01" ...).
Match details (/Default.aspx?pageID=29&macId=<id>) carry the date
and time, stadium, league/season, match code, the full officiating
team (referee, assistants, VAR/AVAR, observer, representative),
goals with minutes, and both starting XIs. Note: TFF's own weekly
referees page (pageID=600) lists the 2./3. Lig rounds with EMPTY
referee columns until appointments are announced close to match
day, so referee data here comes from the match-detail page. The
site is legacy ASP.NET served as windows-1254. Read-only; transport
uses Chrome TLS impersonation; requests are spaced ~0.8s apart.
Built by Mohammad Abbasi (mohammad-abbasi-sh) — https://almanibama.ir · https://mabbasi.ir — Turkey MCP
factory.\
"""


_SOURCE = "tff.org"
_DISCLAIMER = "Unofficial read-only data from tff.org; verify on the site before acting on it."


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)


def _err(e: Exception) -> str:
    return _ok({"error": str(e)})


def _validate_limit(limit: int, lo: int = 1, hi: int = 50) -> int:
    if not lo <= limit <= hi:
        raise ValueError(f"limit must be between {lo} and {hi}")
    return limit


def _league(slug: str) -> tuple[str, dict]:
    slug = (slug or "trendyol-super-lig").strip().lower()
    if slug not in _F.LEAGUES:
        raise ValueError(
            "unknown league — use tff_list_leagues for the 18 slugs: "
            + ", ".join(_F.LEAGUES)
        )
    return slug, _F.LEAGUES[slug]


def _league_html(slug: str, group: str | None) -> tuple[dict, str, list[dict]]:
    """Fetch a league page, resolving the group for multi-group leagues.

    Returns (league, html, groups). For a multi-group league with no
    group given, the first group is used and the groups list is
    included in the output so the caller can pick another one.
    """
    slug, league = _league(slug)
    html_text = _http.fetch_league_html(league["page_id"])
    groups: list[dict] = []
    if league["multi_group"]:
        groups = _F.parse_groups(html_text)
        if groups:
            # Always fetch with the resolved grupID: the default page
            # mixes both groups' fixture tables, so resolve explicitly
            # (default = first group) to keep the data single-group.
            target = _F.resolve_group(groups, group) or groups[0]
            html_text = _http.fetch_league_html(
                league["page_id"], target["id"]
            )
    return league, html_text, groups


@mcp.tool()
def tff_list_leagues() -> str:
    """The 18 Turkish leagues covered (slug, Turkish name, TFF page
    id, whether it has groups, whether a top-scorers page exists).
    No arguments. Use a slug with tff_standings, tff_fixtures and
    tff_top_scorers."""
    return _ok({
            "leagues": [
                {
                    "slug": slug,
                    "name": info["name"],
                    "page_id": info["page_id"],
                    "multi_group": info["multi_group"],
                    "has_top_scorers": info["scorers_page_id"] is not None,
                }
                for slug, info in _F.LEAGUES.items()
            ]
        })


@mcp.tool()
def tff_standings(league: str = "trendyol-super-lig", group: str | None = None) -> str:
    """League standings (puan cetveli): rank, team, played/won/drawn/
    lost, goals for/against, goal difference, points. league: a slug
    from tff_list_leagues (default "trendyol-super-lig"). group: for
    multi-group leagues only — index ("0"), group id, or name
    ("Kırmızı", "Beyaz", "01"); default is the first group, and the
    response lists all groups."""
    try:
        league_info, html_text, groups = _league_html(league, group)
        rows = _F.parse_standings(html_text)
    except (ValueError, _http.TffError) as e:
        return _err(e)
    out: dict = {
        "league": league_info["name"],
        "count": len(rows),
        "standings": rows,
    }
    if groups:
        out["groups"] = groups
        out["group"] = (
            _F.resolve_group(groups, group) or groups[0]
        )["name"]
    return _ok(out)


@mcp.tool()
def tff_fixtures(
    league: str = "trendyol-super-lig",
    week: int | None = None,
    group: str | None = None,
) -> str:
    """League fixtures and results (fikstür): every match-week with
    home/away teams, score (null when not yet played), status
    ("played"/"scheduled"), TFF match id and match-detail URL.
    league: a slug from tff_list_leagues (default
    "trendyol-super-lig"). week: filter to one match-week (e.g. 12);
    omit for all weeks. group: for multi-group leagues only — index,
    group id, or name; default is the first group."""
    try:
        league_info, html_text, groups = _league_html(league, group)
        rows = _F.parse_fixtures(html_text)
    except (ValueError, _http.TffError) as e:
        return _err(e)
    if week is not None:
        rows = [r for r in rows if r["week"] == week]
        if not rows:
            return _err(ValueError(f"no matches in week {week}"))
    out: dict = {
        "league": league_info["name"],
        "count": len(rows),
        "matches": rows,
    }
    if week is not None:
        out["week"] = week
    if groups:
        out["groups"] = groups
        out["group"] = (
            _F.resolve_group(groups, group) or groups[0]
        )["name"]
    return _ok(out)


@mcp.tool()
def tff_match_detail(mac_id: str) -> str:
    """Full detail of one TFF match. mac_id: the TFF match id, as
    returned by tff_fixtures (e.g. "317874"). Returns teams and
    score, date and time, stadium, league/season, match code, the
    officiating team (referee, assistants, VAR/AVAR, observer,
    representative), goals with minutes, and both starting XIs."""
    try:
        if not mac_id or not str(mac_id).strip():
            raise ValueError("mac_id must not be empty")
        html_text = _http.fetch_match_html(str(mac_id).strip())
        data = _F.parse_match_detail(html_text)
    except (ValueError, _http.TffError) as e:
        return _err(e)
    data["mac_id"] = str(mac_id).strip()
    return _ok(data)


@mcp.tool()
def tff_top_scorers(league: str = "trendyol-super-lig", limit: int = 10) -> str:
    """Top scorers (gol krallığı): rank, player, club, goals.
    league: "trendyol-super-lig" (default), "trendyol-1-lig",
    "nesine-2-lig" or "nesine-3-lig" — the four leagues with a TFF
    scorers page. limit 1..50."""
    try:
        _validate_limit(limit)
        _, league_info = _league(league)
        if not league_info["scorers_page_id"]:
            raise ValueError(
                f"TFF publishes no top-scorers page for "
                f"{league_info['name']} — scorers exist only for "
                "trendyol-super-lig, trendyol-1-lig, nesine-2-lig "
                "and nesine-3-lig"
            )
        html_text = _http.fetch_scorers_html(league_info["scorers_page_id"])
        rows = _F.parse_scorers(html_text)
    except (ValueError, _http.TffError) as e:
        return _err(e)
    return _ok({
            "league": league_info["name"],
            "count": min(limit, len(rows)),
            "scorers": rows[:limit],
        })


@mcp.tool()
def tff_health() -> str:
    """Check whether tff.org is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not fetch any listings."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
