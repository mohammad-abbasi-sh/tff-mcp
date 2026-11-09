"""Live tests for tff_mcp — real requests to tff.org.

Requires network + Chrome TLS impersonation (curl-cffi). The server
is polite by design (~0.8s between requests), so this file takes
~20s. Run: python -m unittest discover -s tests -v

Standings/fixtures change during the season; tests assert structure
and sane ranges, not exact tables — except the pinned match detail
(Gaziantep FK 0-2 Kasımpaşa, 6 Nov 2026), which is history.
"""
import json
import unittest

from tff_mcp import football as F
from tff_mcp import http as H

# Pinned historic match: Gaziantep FK 0-2 Kasımpaşa, 6 Nov 2026.
MATCH_ID = "317874"


class TestLiveStandings(unittest.TestCase):
    def test_superlig(self):
        rows = F.parse_standings(H.fetch_league_html("198"))
        self.assertEqual(len(rows), 18)
        self.assertEqual([r["rank"] for r in rows], list(range(1, 19)))
        for r in rows:
            self.assertEqual(r["played"], r["won"] + r["drawn"] + r["lost"])
            self.assertEqual(r["points"], r["won"] * 3 + r["drawn"])

    def test_1lig(self):
        rows = F.parse_standings(H.fetch_league_html("142"))
        self.assertGreater(len(rows), 10)

    def test_2lig_groups(self):
        html_text = H.fetch_league_html("976")
        groups = F.parse_groups(html_text)
        self.assertEqual(len(groups), 2)
        names = {g["name"] for g in groups}
        self.assertEqual(names, {"Beyaz", "Kırmızı"})
        rows = F.parse_standings(
            H.fetch_league_html("976", groups[1]["id"])
        )
        self.assertGreater(len(rows), 10)


class TestLiveFixtures(unittest.TestCase):
    def test_superlig(self):
        rows = F.parse_fixtures(H.fetch_league_html("198"))
        self.assertEqual(len(rows), 34 * 9)
        played = [r for r in rows if r["status"] == "played"]
        scheduled = [r for r in rows if r["status"] == "scheduled"]
        self.assertGreater(len(played), 50)
        self.assertGreater(len(scheduled), 50)
        self.assertTrue(all(r["mac_id"] for r in rows))

    def test_1lig_week1(self):
        rows = F.parse_fixtures(H.fetch_league_html("142"))
        w1 = [r for r in rows if r["week"] == 1]
        self.assertGreater(len(w1), 5)
        self.assertTrue(all(r["status"] == "played" for r in w1))


class TestLiveMatchDetail(unittest.TestCase):
    def test_pinned_match(self):
        d = F.parse_match_detail(H.fetch_match_html(MATCH_ID))
        self.assertEqual(d["home"], "GAZİANTEP FUTBOL KULÜBÜ A.Ş.")
        self.assertEqual(d["away"], "KASIMPAŞA A.Ş.")
        self.assertEqual((d["score_home"], d["score_away"]), (0, 2))
        self.assertEqual(d["date"], "6.11.2026")
        self.assertEqual(d["time"], "20:00")
        self.assertEqual(d["match_code"], "1091")
        officials = {o["name"]: o["role"] for o in d["officials"]}
        self.assertEqual(officials["ÜMİT ÖZTÜRK"], "Hakem")
        self.assertEqual(len(d["goals"]), 2)
        self.assertEqual(len(d["home_lineup"]), 11)
        self.assertEqual(len(d["away_lineup"]), 11)

    def test_unknown_match_redirects_to_empty_page(self):
        # TFF answers an unknown macId with a 302 to a page that
        # carries no match data — the parser must reject it.
        html_text = H.fetch_match_html("999999999")
        with self.assertRaises(ValueError):
            F.parse_match_detail(html_text)

    def test_unknown_match_tool_error_json(self):
        from tff_mcp.server import tff_match_detail

        import json

        data = json.loads(tff_match_detail("999999999"))
        self.assertIn("error", data)


class TestLiveScorers(unittest.TestCase):
    def test_superlig(self):
        rows = F.parse_scorers(H.fetch_scorers_html("821"))
        self.assertGreaterEqual(len(rows), 50)
        self.assertEqual(rows[0]["goals"], max(r["goals"] for r in rows))
        self.assertIn("GALATASARAY", json.dumps(rows, ensure_ascii=False))

    def test_1lig(self):
        rows = F.parse_scorers(H.fetch_scorers_html("822"))
        self.assertGreater(len(rows), 10)


class TestLiveTools(unittest.TestCase):
    """End-to-end through the server module (no MCP transport)."""

    def test_list_leagues_tool(self):
        from tff_mcp.server import tff_list_leagues

        data = json.loads(tff_list_leagues())
        self.assertEqual(len(data["leagues"]), 18)

    def test_standings_tool(self):
        from tff_mcp.server import tff_standings

        data = json.loads(tff_standings("trendyol-super-lig"))
        self.assertEqual(data["count"], 18)
        self.assertEqual(data["standings"][0]["rank"], 1)

    def test_fixtures_tool_week_filter(self):
        from tff_mcp.server import tff_fixtures

        data = json.loads(tff_fixtures("trendyol-super-lig", week=1))
        self.assertEqual(data["week"], 1)
        self.assertEqual(data["count"], 9)

    def test_match_detail_tool(self):
        from tff_mcp.server import tff_match_detail

        data = json.loads(tff_match_detail(MATCH_ID))
        self.assertEqual(data["mac_id"], MATCH_ID)
        self.assertEqual(data["score_away"], 2)

    def test_top_scorers_tool(self):
        from tff_mcp.server import tff_top_scorers

        data = json.loads(tff_top_scorers("trendyol-super-lig", limit=5))
        self.assertEqual(data["count"], 5)
        self.assertEqual(data["scorers"][0]["rank"], 1)

    def test_bad_league_error_json(self):
        from tff_mcp.server import tff_standings

        data = json.loads(tff_standings("no-such-league"))
        self.assertIn("error", data)

    def test_scorers_unsupported_league(self):
        from tff_mcp.server import tff_top_scorers

        data = json.loads(tff_top_scorers("turk-telekom-e-super-lig"))
        self.assertIn("error", data)


if __name__ == "__main__":
    unittest.main()
