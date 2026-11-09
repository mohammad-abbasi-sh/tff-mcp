# tff-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/tff-mcp

Unofficial **read-only** MCP server for tff.org, the Turkish Football Federation (TFF) — league standings (puan cetveli), fixtures and results (fikstür), full match details, and top scorers (gol krallığı) for 18 Turkish leagues, from the Süper Lig down to the youth development leagues.

> Built by Mohammad Abbasi as part of the "Turkey MCP factory" (Sepehr-style pipeline). Not affiliated with tff.org or the TFF.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "tff": {
      "command": "uvx",
      "args": ["tff-mcp"]
    }
  }
}
```

Or run locally: `python -m tff_mcp.server` (needs `mcp<2`, `curl-cffi`).

## Tools

| Tool | Description |
|------|-------------|
| `tff_list_leagues` | The 18 covered leagues (slug, Turkish name, TFF page id, multi-group flag, top-scorers availability) |
| `tff_standings` | League standings — `league` slug (default "trendyol-super-lig"); `group` for multi-group leagues: index ("0"), group id, or name ("Kırmızı", "Beyaz", "01"); rank, team, played/won/drawn/lost, goals for/against, goal difference, points |
| `tff_fixtures` | Fixtures and results — `league` slug; `week` to filter to one match-week; `group` for multi-group leagues; home/away, score (null when not yet played), status ("played"/"scheduled"), TFF match id and match-detail URL |
| `tff_match_detail` | Full detail of one match — `mac_id` (as returned by `tff_fixtures`, e.g. "317874"); teams and score, date/time, stadium, league/season, match code, the officiating team (referee, assistants, VAR/AVAR, observer, representative), goals with minutes, both starting XIs |
| `tff_top_scorers` | Top scorers — `league`: "trendyol-super-lig" (default), "trendyol-1-lig", "nesine-2-lig" or "nesine-3-lig" (the four leagues with a TFF scorers page); `limit` 1..50 |

Example output (`tff_match_detail` / Gaziantep FK 0–2 Kasımpaşa, 6 Nov 2026):

```json
{"home": "GAZİANTEP FUTBOL KULÜBÜ A.Ş.", "away": "KASIMPAŞA A.Ş.",
 "score_home": 0, "score_away": 2, "date": "6.11.2026", "time": "20:00",
 "stadium": "GAZİANTEP STADYUMU - GAZİANTEP - ŞEHİTKAMİL",
 "league": "Trendyol Süper Lig Adnan Süvari Sezonu (Profesyonel Takım)",
 "match_code": "1091",
 "officials": [{"name": "ÜMİT ÖZTÜRK", "role": "Hakem"},
               {"name": "ERKAN ENGİN", "role": "VAR"}],
 "goals": [{"player": "HARIS HAJRADINOVIC", "minute": 3, "type": "F"},
           {"player": "ADRIAN DAWID BENEDYCZAK", "minute": 21, "type": "P"}]}
```

## How it works

tff.org serves its league pages fully server-rendered — no login, no API key, no session cookies. Standings live in `<table class="s-table">` (header O G B M A Y AV P); fixtures in `<table class="fiksturListesiTable">` ("N.Hafta" headers, match rows with home club link, score link `pageID=29&macId=...`, away club link — unplayed matches show " - "). Multi-group leagues (Nesine 2. Lig, Nesine 3. Lig, BAL, women's and youth leagues) expose their groups as `?pageID=<id>&grupID=<n>` links. Match details carry the teams in `lnkTakim1`/`lnkTakim2`, scores in `MacDetaySayi` spans, league/season in `lblOrganizasyonAdi`, match code in `lblKod`, date/time in `lblTarih`, the stadium as text between the code and the date, officials as `NAME(ROLE)` pairs, goals as "NAME,3.dk (F)" entries, and the starting XIs in the `grdTakim1/2_rptKadrolar` repeaters. Top scorers come from the `rptGolKralligi` repeater (pages 821/822/823/824). The site is legacy ASP.NET served as windows-1254, decoded explicitly. One site feature is documented, not faked: the weekly referees page (`pageID=600`) lists the 2./3. Lig rounds with EMPTY referee columns until appointments are announced close to match day — so referee data comes from the match-detail page instead. Transport uses Chrome TLS impersonation (`curl-cffi`, `chrome120`); requests are spaced ~0.8s apart; everything is read-only.

## Install

```bash
uvx tff-mcp        # run directly (needs uv)
# or
pip install tff-mcp
tff-mcp    # starts the MCP server on stdio
```

## Tests

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Offline tests run on recorded fixtures (real pages fetched 2026-11-09); live tests hit tff.org. 37/37 green at build time (20 offline + 17 live) plus an MCP stdio smoke test.

## Roadmap

- Disciplinary decisions (PFDK/AFDK pages) and suspended players (pageID=633)
- Club pages (pageID=28&kulupID=...) — squad lists
- National-team matches (pageID=425)

## License

MIT — see [LICENSE](LICENSE).
