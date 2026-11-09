"""Offline tests for tff_mcp — recorded TFF fixtures, no network.

Fixtures recorded 2026-11-09 from tff.org (plain HTTP 200):
- league-superlig.html: Trendyol Süper Lig page (pageID=198)
- league-2lig.html: Nesine 2. Lig page (pageID=976, multi-group)
- match-detail.html: Gaziantep FK 0-2 Kasımpaşa (pageID=29&macId=317874)
- scorers-superlig.html: Süper Lig Gol Krallığı (pageID=821)

Run: python -m unittest discover -s tests -v
"""
import os
import unittest

from tff_mcp import football as F

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name: str) -> str:
    with open(os.path.join(FIX, name), encoding="windows-1254") as f:
        return f.read()


class TestLeagues(unittest.TestCase):
    def test_catalog(self):
        self.assertEqual(len(F.LEAGUES), 18)
        self.assertEqual(F.LEAGUES["trendyol-super-lig"]["page_id"], "198")
        self.assertTrue(F.LEAGUES["nesine-2-lig"]["multi_group"])
        self.assertFalse(F.LEAGUES["trendyol-super-lig"]["multi_group"])
        self.assertEqual(
            F.LEAGUES["trendyol-super-lig"]["scorers_page_id"], "821"
        )
        self.assertIsNone(
            F.LEAGUES["regional-amateur-league-bal"]["scorers_page_id"]
        )


class TestStandings(unittest.TestCase):
    def setUp(self):
        self.html = _read("league-superlig.html")

    def test_superlig_18_teams(self):
        rows = F.parse_standings(self.html)
        self.assertEqual(len(rows), 18)
        top = rows[0]
        self.assertEqual(top["rank"], 1)
        self.assertEqual(top["team"], "GALATASARAY A.Ş.")
        self.assertEqual(top["club_id"], "3604")
        self.assertEqual(top["played"], 11)
        self.assertEqual(top["won"], 9)
        self.assertEqual(top["drawn"], 1)
        self.assertEqual(top["lost"], 1)
        self.assertEqual(top["points"], 28)
        self.assertEqual(
            top["goal_difference"],
            top["goals_for"] - top["goals_against"],
        )

    def test_ranks_sequential(self):
        rows = F.parse_standings(self.html)
        self.assertEqual([r["rank"] for r in rows], list(range(1, 19)))
        for r in rows:
            self.assertEqual(r["played"], r["won"] + r["drawn"] + r["lost"])
            self.assertEqual(r["points"], r["won"] * 3 + r["drawn"])

    def test_no_table(self):
        with self.assertRaises(ValueError):
            F.parse_standings("<html><body>no table here</body></html>")


class TestGroups(unittest.TestCase):
    def test_2lig_two_groups(self):
        groups = F.parse_groups(_read("league-2lig.html"))
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0], {"id": "3541", "name": "Beyaz"})
        self.assertEqual(groups[1], {"id": "3542", "name": "Kırmızı"})

    def test_resolve_group(self):
        groups = [{"id": "3541", "name": "Beyaz"},
                   {"id": "3542", "name": "Kırmızı"}]
        self.assertEqual(F.resolve_group(groups, "0"), groups[0])
        self.assertEqual(F.resolve_group(groups, "1"), groups[1])
        self.assertEqual(F.resolve_group(groups, "kırmızı"), groups[1])
        self.assertEqual(F.resolve_group(groups, "KIRMIZI"), groups[1])
        self.assertEqual(F.resolve_group(groups, "3542"), groups[1])
        self.assertIsNone(F.resolve_group(groups, None))
        with self.assertRaises(ValueError):
            F.resolve_group(groups, "Mavi")


class TestFixtures(unittest.TestCase):
    def setUp(self):
        self.rows = F.parse_fixtures(_read("league-superlig.html"))

    def test_34_weeks_306_matches(self):
        self.assertEqual(len(self.rows), 34 * 9)
        weeks = sorted({r["week"] for r in self.rows})
        self.assertEqual(weeks, list(range(1, 35)))
        for w in range(1, 35):
            self.assertEqual(
                len([r for r in self.rows if r["week"] == w]), 9
            )

    def test_week1_first_match(self):
        w1 = [r for r in self.rows if r["week"] == 1]
        first = w1[0]
        self.assertEqual(first["home"], "GALATASARAY A.Ş.")
        self.assertEqual(first["away"], "ARCA ÇORUM FK")
        self.assertEqual(first["score_home"], 2)
        self.assertEqual(first["score_away"], 2)
        self.assertEqual(first["status"], "played")
        self.assertEqual(first["mac_id"], "317790")
        self.assertIn("macId=317790", first["match_url"])

    def test_unplayed_match_scheduled(self):
        w12 = [r for r in self.rows if r["week"] == 12]
        self.assertEqual(len(w12), 9)
        for r in w12:
            self.assertEqual(r["status"], "scheduled")
            self.assertIsNone(r["score_home"])
            self.assertIsNone(r["score_away"])
            self.assertIsNotNone(r["mac_id"])
        derby = [r for r in w12 if r["home"] == "GALATASARAY A.Ş."][0]
        self.assertEqual(derby["away"], "SAMSUNSPOR A.Ş.")

    def test_no_fixture_table(self):
        with self.assertRaises(ValueError):
            F.parse_fixtures("<html><body>no fixtures</body></html>")


class TestMatchDetail(unittest.TestCase):
    def setUp(self):
        self.d = F.parse_match_detail(_read("match-detail.html"))

    def test_teams_and_score(self):
        self.assertEqual(self.d["home"], "GAZİANTEP FUTBOL KULÜBÜ A.Ş.")
        self.assertEqual(self.d["away"], "KASIMPAŞA A.Ş.")
        self.assertEqual(self.d["score_home"], 0)
        self.assertEqual(self.d["score_away"], 2)
        self.assertEqual(self.d["home_club_id"], "3672")
        self.assertEqual(self.d["away_club_id"], "39")

    def test_meta(self):
        self.assertEqual(
            self.d["league"],
            "Trendyol Süper Lig Adnan Süvari Sezonu (Profesyonel Takım)",
        )
        self.assertEqual(self.d["match_code"], "1091")
        self.assertEqual(self.d["date"], "6.11.2026")
        self.assertEqual(self.d["time"], "20:00")
        self.assertEqual(
            self.d["stadium"], "GAZİANTEP STADYUMU - GAZİANTEP - ŞEHİTKAMİL"
        )

    def test_officials(self):
        officials = {o["name"]: o["role"] for o in self.d["officials"]}
        self.assertEqual(officials["ÜMİT ÖZTÜRK"], "Hakem")
        self.assertEqual(officials["GÖKMEN BALTACI"], "1. Yardımcı Hakem")
        self.assertEqual(officials["YUSUF SUSUZ"], "2. Yardımcı Hakem")
        self.assertEqual(officials["ERDEM MERTOĞLU"], "Dördüncü Hakem")
        self.assertEqual(officials["ERKAN ENGİN"], "VAR")
        self.assertEqual(officials["SÜLEYMAN ÖZAY"], "AVAR")
        self.assertEqual(officials["BÜLENT GÖKÇÜ"], "Gözlemci")
        self.assertEqual(officials["SERKAN YURDABAK"], "Temsilci")

    def test_goals(self):
        self.assertEqual(
            self.d["goals"],
            [
                {"player": "HARIS HAJRADINOVIC", "minute": 3, "type": "F"},
                {
                    "player": "ADRIAN DAWID BENEDYCZAK",
                    "minute": 21,
                    "type": "P",
                },
            ],
        )

    def test_lineups(self):
        self.assertEqual(len(self.d["home_lineup"]), 11)
        self.assertEqual(len(self.d["away_lineup"]), 11)
        self.assertEqual(
            self.d["home_lineup"][0],
            {"number": 35, "player": "MEHMET ATABERK DADAKDENİZ"},
        )

    def test_bad_page(self):
        with self.assertRaises(ValueError):
            F.parse_match_detail("<html><body>not a match page</body></html>")


class TestScorers(unittest.TestCase):
    def setUp(self):
        self.rows = F.parse_scorers(_read("scorers-superlig.html"))

    def test_leader(self):
        self.assertGreaterEqual(len(self.rows), 100)
        top = self.rows[0]
        self.assertEqual(top["rank"], 1)
        self.assertEqual(top["player"], "GIFT EMMANUEL ORBAN")
        self.assertEqual(top["club"], "AMED SPORTİF FAALİYETLER")
        self.assertEqual(top["goals"], 10)
        self.assertEqual(top["player_id"], "2935123")
        self.assertEqual(top["club_id"], "3678")

    def test_top_four(self):
        self.assertEqual(
            [(r["player"], r["goals"]) for r in self.rows[:4]],
            [
                ("GIFT EMMANUEL ORBAN", 10),
                ("DUSAN VLAHOVIC", 9),
                ("MOHAMED SALAH HAMED MAHROUS GHALY", 9),
                ("VICTOR JAMES OSIMHEN", 9),
            ],
        )

    def test_goals_nonincreasing(self):
        goals = [r["goals"] for r in self.rows]
        self.assertEqual(goals, sorted(goals, reverse=True))

    def test_no_scorers(self):
        with self.assertRaises(ValueError):
            F.parse_scorers("<html><body>no scorers</body></html>")


if __name__ == "__main__":
    unittest.main()
