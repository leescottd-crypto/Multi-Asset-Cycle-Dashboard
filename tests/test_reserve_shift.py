import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReserveShiftExhibitTests(unittest.TestCase):
    def test_source_snapshot_contract(self):
        payload = json.loads((ROOT / "public/data/reserve-shift.json").read_text())
        self.assertEqual(payload["chart"]["unit"], "% of foreign central-bank reserves")
        self.assertEqual(payload["chart"]["cadence"], "Q2 of each year")
        self.assertEqual([row["gold"] for row in payload["chart"]["series"]], [13, 14, 15, 17, 24])
        self.assertEqual([row["us_debt"] for row in payload["chart"]["series"]], [28, 27, 26, 24, 23])
        self.assertEqual(payload["q2_2026_buying"]["tonnes"], 289)
        self.assertEqual(payload["ecb_cross_check"]["gold_share"], 27)
        self.assertEqual(payload["ecb_cross_check"]["us_treasuries_share"], 22)
        self.assertGreaterEqual(len(payload["sources"]), 3)

    def test_dashboard_wires_reserve_tab_and_renderer(self):
        html = (ROOT / "index.html").read_text()
        script = (ROOT / "src/app.js").read_text()
        css = (ROOT / "src/styles.css").read_text()
        for marker in [
            'data-macro-tab="reserves"',
            'id="macroReservesPane"',
            'Reserve Shift',
        ]:
            self.assertIn(marker, html)
        for marker in [
            "let reserveShiftData;",
            "function renderReserveShift()",
            "function reserveShiftChart(data)",
            "reserve-shift.json",
            "reserves: 'macroReservesPane'",
        ]:
            self.assertIn(marker, script)
        for marker in [".reserve-shift-layout", ".reserve-shift-chart", ".reserve-shift-stat"]:
            self.assertIn(marker, css)

    def test_reserve_shift_is_easy_to_open_directly(self):
        html = (ROOT / "index.html").read_text()
        script = (ROOT / "src/app.js").read_text()

        self.assertIn('href="#reserve-shift"', html)
        self.assertIn("Open Reserve Shift exhibit", html)
        self.assertIn("function activateMacroTab", script)
        self.assertIn("window.location.hash === '#reserve-shift'", script)


if __name__ == "__main__":
    unittest.main()
