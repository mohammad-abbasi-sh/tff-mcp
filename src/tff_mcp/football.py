"""Stdlib parsing for tff.org (Turkish Football Federation) pages.

Verified live 2026-11-09 against real pages (fixtures in tests/):
- League page (/default.aspx?pageID=<id>, ~330KB for Süper Lig):
  standings = <table class="s-table">, header O G B M A Y AV P
  (played/won/drawn/lost/goals-for/goals-against/goal-diff/points),
  rows "1.GALATASARAY A.Ş." with a kulupID club link; fixtures =
  <table class="fiksturListesiTable"> with "N.Hafta" header rows and
  match rows (home club link, score link pageID=29&macId=..., away
  club link). Unplayed matches show " - " as the score; the date
  lives on the match-detail page. Weeks 1..34 (Süper Lig).
  Multi-group leagues (2./3. Lig, BAL, women's, youth) expose their
  groups as ?pageID=<id>&grupID=<n> links (#grp / #hmac, deduped).
- Match detail (pageID=29&macId=..., ~165KB): team names in
  lnkTakim1/lnkTakim2, scores in MacDetaySayi spans, league/season
  in lblOrganizasyonAdi, match code in lblKod, date/time in lblTarih
  ("6.11.2026 - 20:00"), stadium as plain text between the code and
  the date, officials as NAME(ROLE) pairs (Hakem, 1./2. Yardımcı
  Hakem, Dördüncü Hakem, VAR, AVAR, Gözlemci, Temsilci), goals as
  "NAME,3.dk (F)" entries after the "Goller" heading, starting XIs
  in the grdTakim1/2_rptKadrolar repeaters (formaNo + lnkOyuncu).
- Top scorers (pageID=821/822/823/824): rptGolKralligi repeater —
  lblOyuncu (player, kisiID link), lblKulup (club, kulupID link),
  lblGolSayisi (goals). Süper Lig lists ~140 scorers.
- The weekly referees page (pageID=600) is NOT parsed: its Hakemler
  columns are empty (&nbsp;) for the upcoming 2./3. Lig rounds —
  referees are only announced close to match day — so referees are
  served from the match-detail page instead (played matches carry
  the full officiating team).
"""
from __future__ import annotations

import html
import re

# slug -> league page. "multi_group" leagues expose ?grupID= links.
# scorers_page_id is None where TFF publishes no Gol Krallığı page.
LEAGUES = {
    "trendyol-super-lig": {
        "page_id": "198", "name": "Trendyol Süper Lig",
        "multi_group": False, "scorers_page_id": "821",
    },
    "trendyol-1-lig": {
        "page_id": "142", "name": "Trendyol 1. Lig",
        "multi_group": False, "scorers_page_id": "822",
    },
    "nesine-2-lig": {
        "page_id": "976", "name": "Nesine 2. Lig",
        "multi_group": True, "scorers_page_id": "823",
    },
    "nesine-3-lig": {
        "page_id": "971", "name": "Nesine 3. Lig",
        "multi_group": True, "scorers_page_id": "824",
    },
    "regional-amateur-league-bal": {
        "page_id": "1596", "name": "Bölgesel Amatör Lig",
        "multi_group": True, "scorers_page_id": None,
    },
    "turkcell-womens-super-lig": {
        "page_id": "1000", "name": "Suwen Kadın Futbol Süper Ligi",
        "multi_group": False, "scorers_page_id": None,
    },
    "womens-1-league": {
        "page_id": "1602", "name": "TFF Kadınlar 1. Ligi",
        "multi_group": True, "scorers_page_id": None,
    },
    "womens-2-league": {
        "page_id": "1001", "name": "TFF Kadınlar 2. Ligi",
        "multi_group": True, "scorers_page_id": None,
    },
    "womens-3-league": {
        "page_id": "1298", "name": "TFF Kadınlar 3. Ligi",
        "multi_group": True, "scorers_page_id": None,
    },
    "turk-telekom-e-super-lig": {
        "page_id": "1610", "name": "Türk Telekom eSüper Lig",
        "multi_group": False, "scorers_page_id": None,
    },
    "u19-paf-league": {
        "page_id": "1750", "name": "U19 PAF Ligi",
        "multi_group": True, "scorers_page_id": None,
    },
    "u19-development-league": {
        "page_id": "1751", "name": "U19 Gelişim Ligi",
        "multi_group": True, "scorers_page_id": None,
    },
    "u17-development-league": {
        "page_id": "1752", "name": "U17 Gelişim Ligi",
        "multi_group": True, "scorers_page_id": None,
    },
    "u16-development-league": {
        "page_id": "1753", "name": "U16 Gelişim Ligi",
        "multi_group": True, "scorers_page_id": None,
    },
    "u15-development-league": {
        "page_id": "1754", "name": "U15 Gelişim Ligi",
        "multi_group": True, "scorers_page_id": None,
    },
    "u14-development-league": {
        "page_id": "1755", "name": "U14 Gelişim Ligi",
        "multi_group": True, "scorers_page_id": None,
    },
    "u13-development-league": {
        "page_id": "1762", "name": "U13 Gelişim Ligi",
        "multi_group": True, "scorers_page_id": None,
    },
    "youth-infrastructure-development": {
        "page_id": "1494", "name": "Futbol Altyapı Gelişim Ligi",
        "multi_group": True, "scorers_page_id": None,
    },
}

_TR_UPPER_TO_LOWER = str.maketrans({
    "İ": "i", "I": "ı", "Ş": "ş", "Ğ": "ğ",
    "Ü": "ü", "Ö": "ö", "Ç": "ç",
})


def tr_lower(s: str) -> str:
    """Turkish-aware lowercase (str.lower() mangles İ -> i + dot)."""
    return s.translate(_TR_UPPER_TO_LOWER).lower()


def _clean(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _int_or_none(text: str) -> int | None:
    text = _clean(text).replace(".", "").replace(",", "")
    try:
        return int(text)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------- groups

_GROUP_LINK_RE = re.compile(
    r'<a[^>]*href="[^"]*grupID=(\d+)[^"]*"[^>]*>(.*?)</a>', re.S | re.I
)


def parse_groups(html_text: str) -> list[dict]:
    """Multi-group league page -> [{id, name}] in page order.

    Each group appears twice (#grp / #hmac links); dedup by id.
    """
    groups: list[dict] = []
    seen: set[str] = set()
    for m in _GROUP_LINK_RE.finditer(html_text):
        gid, raw_name = m.group(1), _clean(m.group(2))
        if gid in seen:
            continue
        seen.add(gid)
        groups.append({"id": gid, "name": raw_name or f"Grup {gid}"})
    return groups


def resolve_group(groups: list[dict], group: str | None) -> dict | None:
    """Pick a group by index ("0"), id, or name substring (TR-aware).

    Returns the group dict, or None when `group` is None (caller uses
    the default = first group) — the caller decides the default.
    """
    if group is None:
        return None
    g = group.strip()
    if g.isdigit():
        idx = int(g)
        if 0 <= idx < len(groups):
            return groups[idx]
        for grp in groups:
            if grp["id"] == g:
                return grp
        raise ValueError(
            f"group {g!r} not found — this league has {len(groups)} "
            f"groups: {', '.join(x['name'] for x in groups)}"
        )
    needle = tr_lower(g)
    for grp in groups:
        if needle in tr_lower(grp["name"]):
            return grp
    raise ValueError(
        f"group {g!r} not found — available groups: "
        f"{', '.join(x['name'] for x in groups)}"
    )


# ---------------------------------------------------------------- standings

def parse_standings(html_text: str) -> list[dict]:
    """s-table -> [{rank, team, club_id, played, won, drawn, lost,
    goals_for, goals_against, goal_difference, points}]."""
    m = re.search(
        r'<table[^>]*class="s-table"[^>]*>(.*?)</table>', html_text, re.S
    )
    if not m:
        raise ValueError("no standings table (s-table) found on this page")
    rows: list[dict] = []
    for rm in re.finditer(r"<tr[^>]*>(.*?)</tr>", m.group(1), re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", rm.group(1), re.S)
        if len(cells) < 9:
            continue
        first = _clean(cells[0])
        rank_m = re.match(r"(\d+)\.\s*(.+)", first)
        if not rank_m:
            continue  # header row ("O G B M ...") or spacer
        club_m = re.search(r"kulupID=(\d+)", cells[0], re.I)
        nums = [_int_or_none(c) for c in cells[1:9]]
        if any(n is None for n in nums):
            continue
        rows.append({
            "rank": int(rank_m.group(1)),
            "team": rank_m.group(2).strip(),
            "club_id": club_m.group(1) if club_m else None,
            "played": nums[0],
            "won": nums[1],
            "drawn": nums[2],
            "lost": nums[3],
            "goals_for": nums[4],
            "goals_against": nums[5],
            "goal_difference": nums[6],
            "points": nums[7],
        })
    if not rows:
        raise ValueError("standings table found but no team rows parsed")
    return rows


# ---------------------------------------------------------------- fixtures

_WEEK_RE = re.compile(r"(\d+)\.Hafta")
_FIX_ANCHOR_RE = re.compile(
    r'<a[^>]*href="([^"]*?pageID=(?:28|29)[^"]*)"[^>]*>([^<]*)</a>', re.I
)


def parse_fixtures(html_text: str) -> list[dict]:
    """Fixture table(s) -> [{week, home, home_club_id, away,
    away_club_id, score_home, score_away, status, mac_id, match_url}].

    Scans from the first fiksturListesiTable; week headers ("N.Hafta")
    set the week for the matches that follow. Unplayed matches show
    " - " as the score (status "scheduled"); played ones "2 - 2".
    """
    start = html_text.find("fiksturListesiTable")
    if start < 0:
        raise ValueError("no fixture table (fiksturListesiTable) found")
    region = html_text[start:]
    # Week header positions, in order.
    weeks = [(m.start(), int(m.group(1))) for m in _WEEK_RE.finditer(region)]
    matches: list[dict] = []
    pending: list[tuple[str, str, str]] = []  # (kind, href, text)
    for m in _FIX_ANCHOR_RE.finditer(region):
        href, text = m.group(1), _clean(m.group(2))
        if "pageID=28" in href or "pageId=28" in href:
            kind = "club"
        elif "pageID=29" in href or "pageId=29" in href:
            kind = "score"
        else:
            continue
        pending.append((kind, href, text, m.start()))
        if len(pending) == 3 and [p[0] for p in pending] == [
            "club", "score", "club",
        ]:
            ( _, home_href, home, home_pos), (
                _, score_href, score, _,
            ), (_, away_href, away, _) = pending
            mac_m = re.search(r"macId=(\d+)", score_href, re.I)
            home_m = re.search(r"kulupId=(\d+)", home_href, re.I)
            away_m = re.search(r"kulupId=(\d+)", away_href, re.I)
            week = 0
            for pos, w in weeks:
                if pos <= home_pos:
                    week = w
                else:
                    break
            score_m = re.match(r"(\d+)\s*-\s*(\d+)", score)
            if score_m:
                sh, sa, status = int(score_m.group(1)), int(score_m.group(2)), "played"
            else:
                sh, sa, status = None, None, "scheduled"
            mac_id = mac_m.group(1) if mac_m else None
            matches.append({
                "week": week,
                "home": home,
                "home_club_id": home_m.group(1) if home_m else None,
                "away": away,
                "away_club_id": away_m.group(1) if away_m else None,
                "score_home": sh,
                "score_away": sa,
                "status": status,
                "mac_id": mac_id,
                "match_url": (
                    "https://www.tff.org/Default.aspx?pageID=29&macId=" + mac_id
                    if mac_id else None
                ),
            })
            pending = []
        elif len(pending) >= 3:
            pending = pending[-2:]
    if not matches:
        raise ValueError("fixture table found but no matches parsed")
    return matches


# ---------------------------------------------------------------- match detail

_OFFICIAL_ROLES = {
    "Hakem", "1. Yardımcı Hakem", "2. Yardımcı Hakem",
    "Dördüncü Hakem", "VAR", "AVAR", "Gözlemci", "Temsilci",
}

_TEAM_RE = re.compile(
    r'lnkTakim([12])[^>]*href="[^"]*kulupId=(\d+)[^"]*"[^>]*>([^<]+)</a>'
)
_SCORE_RE = re.compile(
    r'<p class="MacDetaySayi">\s*<span[^>]*>(\d+)</span>', re.S
)
_SPAN_RE = re.compile(r'{id}[^>]*>([^<]*)</')


def _span(html_text: str, frag: str) -> str:
    # Span content may hold a <br/> (lblOrganizasyonAdi does), so
    # capture up to </span> and strip tags afterwards.
    m = re.search(rf'{re.escape(frag)}[^>]*>(.*?)</span>', html_text, re.S)
    return _clean(m.group(1)) if m else ""


def parse_match_detail(html_text: str) -> dict:
    """Match detail page -> teams, score, date/time, stadium, league,
    match code, officials, goals, starting lineups."""
    teams: dict[str, dict] = {}
    for m in _TEAM_RE.finditer(html_text):
        teams[m.group(1)] = {
            "name": _clean(m.group(3)),
            "club_id": m.group(2),
        }
    if "1" not in teams or "2" not in teams:
        raise ValueError("match detail page: team names not found")
    scores = [int(x) for x in _SCORE_RE.findall(html_text)[:2]]
    if len(scores) != 2:
        raise ValueError("match detail page: scores not found")

    out: dict = {
        "home": teams["1"]["name"],
        "home_club_id": teams["1"]["club_id"],
        "away": teams["2"]["name"],
        "away_club_id": teams["2"]["club_id"],
        "score_home": scores[0],
        "score_away": scores[1],
        "league": _span(html_text, "lblOrganizasyonAdi"),
        "match_code": _span(html_text, "lblKod"),
    }
    date_raw = _span(html_text, "lblTarih")  # "6.11.2026 - 20:00"
    dm = re.match(r"(\d{1,2}\.\d{1,2}\.\d{4})\s*-\s*(\d{2}:\d{2})", date_raw)
    if dm:
        out["date"], out["time"] = dm.group(1), dm.group(2)

    text = _clean(html_text)
    # Stadium: plain text between the match code and the date.
    sm = re.search(
        r"Maç Kodu:\s*\d+\s+(.+?)\s+\d{1,2}\.\d{1,2}\.\d{4}\s*-\s*\d{2}:\d{2}",
        text,
    )
    if sm:
        out["stadium"] = sm.group(1).strip()

    # Officials: NAME(ROLE) pairs after the date, before the lineups.
    tail = text
    if dm:
        tail = text[text.find(dm.group(0)) + len(dm.group(0)):]
    tail = tail.split("İlk 11")[0]
    officials: list[dict] = []
    for om in re.finditer(
        r"([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ ]+?)\(([^)]+)\)", tail
    ):
        name, role = om.group(1).strip(), om.group(2).strip()
        if role in _OFFICIAL_ROLES and len(name) >= 3:
            officials.append({"name": name, "role": role})
    if officials:
        out["officials"] = officials

    # Goals: "NAME,3.dk (F)" entries after the Goller heading.
    gm = re.search(r"\bGoller\b\s*(.*?)(?:İlk 11|$)", text, re.S)
    goals: list[dict] = []
    if gm:
        for g in re.finditer(
            r"([^,()]+?),\s*(\d+)\.dk\s*\(([^)]*)\)", gm.group(1)
        ):
            goals.append({
                "player": g.group(1).strip(),
                "minute": int(g.group(2)),
                "type": g.group(3).strip(),
            })
    out["goals"] = goals

    # Starting XIs: grdTakim1/2_rptKadrolar (formaNo + lnkOyuncu).
    for side, key in (("1", "home_lineup"), ("2", "away_lineup")):
        lineup: list[dict] = []
        for lm in re.finditer(
            rf"grdTakim{side}_rptKadrolar_ctl\d+_formaNo[^>]*>"
            r"(\d+)\.</span>\s*<a[^>]*lnkOyuncu[^>]*>([^<]+)</a>",
            html_text,
        ):
            lineup.append({
                "number": int(lm.group(1)),
                "player": _clean(lm.group(2)),
            })
        if lineup:
            out[key] = lineup
    return {k: v for k, v in out.items() if v not in (None, "", [])}


# ---------------------------------------------------------------- top scorers

_SCORER_RE = re.compile(
    r"rptGolKralligi_ctl\d+_lblOyuncu[^>]*"
    r'href="[^"]*kisiID=(\d+)[^"]*"[^>]*>([^<]+)</a>',
    re.I,
)


def parse_scorers(html_text: str) -> list[dict]:
    """Top-scorers repeater -> [{rank, player, player_id, club,
    club_id, goals}] in table order (most goals first)."""
    rows: list[dict] = []
    for m in _SCORER_RE.finditer(html_text):
        player_id, player = m.group(1), _clean(m.group(2))
        rest = html_text[m.end():m.end() + 800]
        club_m = re.search(
            r"lblKulup[^>]*href=\"[^\"]*kulupID=(\d+)[^\"]*\"[^>]*>"
            r"([^<]+)</a>",
            rest,
            re.I,
        )
        goals_m = re.search(r"lblGolSayisi[^>]*>(\d+)<", rest)
        if not club_m or not goals_m:
            continue
        rows.append({
            "rank": len(rows) + 1,
            "player": player,
            "player_id": player_id,
            "club": _clean(club_m.group(2)),
            "club_id": club_m.group(1),
            "goals": int(goals_m.group(1)),
        })
    if not rows:
        raise ValueError("no top scorers parsed from this page")
    return rows
