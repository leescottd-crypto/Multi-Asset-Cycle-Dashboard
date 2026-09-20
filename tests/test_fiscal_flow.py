from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("fiscal_flow", ROOT / "scripts" / "fiscal_flow.py")
fiscal_flow = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(fiscal_flow)


class FiscalFlowDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = json.loads((ROOT / "public" / "data" / "fiscal-flow.json").read_text())
        cls.manifest = json.loads((ROOT / "data" / "fiscal-flow" / "manifest.json").read_text())
        cls.snapshots = cls.client["years"] + [cls.client["current"]]

    def test_has_twenty_frozen_years_plus_current(self):
        self.assertEqual(20, len(self.client["years"]))
        self.assertEqual(list(range(2006, 2026)), [row["fiscal_year"] for row in self.client["years"]])
        self.assertEqual(21, len(self.snapshots))
        self.assertEqual(21, len({row["fiscal_year"] for row in self.snapshots}))
        self.assertTrue(all(row["status"] == "final-frozen" for row in self.client["years"]))

    def test_reconciliation_and_offsets(self):
        for row in self.snapshots:
            with self.subTest(year=row["fiscal_year"]):
                receipt_tolerance = 2_000_000 if row["fiscal_year"] <= 2014 else 2
                outlay_tolerance = 2_000_000 if row["fiscal_year"] <= 2014 else 3
                self.assertLessEqual(abs(row["reconciliation"]["receipt_detail_less_total_dollars"]), receipt_tolerance)
                self.assertLessEqual(abs(row["reconciliation"]["outlay_detail_less_total_dollars"]), outlay_tolerance)
                self.assertEqual(0, row["reconciliation"]["identity_difference_dollars"])
                self.assertTrue(all(item["amount_dollars"] >= 0 for item in row["positive_outlays"]))
                self.assertTrue(all(item["amount_dollars"] < 0 for item in row["offsetting_outlays"]))

    def test_fy2006_expected_values(self):
        row = self.client["years"][0]
        self.assertEqual(2_406_681_000_000, row["total_receipts_dollars"])
        self.assertEqual(2_654_379_000_000, row["net_outlays_dollars"])
        self.assertEqual(247_698_000_000, row["deficit_dollars"])

    def test_current_is_latest_available_and_has_same_period_comparison(self):
        current = self.client["current"]
        self.assertGreaterEqual(current["fiscal_year"], 2026)
        self.assertEqual("current-ytd", current["status"])
        self.assertRegex(current["period_end"], rf"^{current['fiscal_year']}-\d{{2}}-\d{{2}}$")
        self.assertEqual(current["fiscal_year"] - 1, current["prior_year_same_period"]["fiscal_year"])
        self.assertEqual(current["period_end"][5:], current["prior_year_same_period"]["period_through"])

    def test_manifest_hashes_and_source_urls(self):
        self.assertEqual(20, len(self.manifest["archive"]))
        for entry in self.manifest["archive"]:
            path = ROOT / entry["file"]
            self.assertTrue(entry["source_url"].startswith("https://"))
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry["sha256"])
        self.assertTrue(self.manifest["current"]["source_url"].startswith("https://"))
        self.assertTrue(self.manifest["debt"]["source_url"].startswith("https://"))
        debt_path = ROOT / self.manifest["debt"]["file"]
        self.assertEqual(hashlib.sha256(debt_path.read_bytes()).hexdigest(), self.manifest["debt"]["sha256"])
        self.assertTrue(all(row["source_url"] for row in self.snapshots))

    def test_total_public_debt_covers_every_slice(self):
        debt = self.client["debt"]
        self.assertEqual(set(map(str, range(2006, 2026))), set(debt["by_fiscal_year"]))
        annual = [debt["by_fiscal_year"][str(year)]["total_public_debt_outstanding_dollars"] for year in range(2006, 2026)]
        self.assertTrue(all(amount > 0 for amount in annual))
        self.assertTrue(all(current > prior for prior, current in zip(annual, annual[1:])))
        self.assertGreater(debt["current"]["total_public_debt_outstanding_dollars"], 40_000_000_000_000)
        self.assertGreater(debt["current"]["total_public_debt_outstanding_dollars"], annual[-1])

    def test_archive_refuses_overwrite_without_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp)
            with patch.object(fiscal_flow, "ARCHIVE", archive):
                sample = dict(self.client["years"][0])
                fiscal_flow.write_archive(sample)
                with self.assertRaises(FileExistsError):
                    fiscal_flow.write_archive(sample)
                fiscal_flow.write_archive(sample, migrate=True)

    def test_current_only_refresh_does_not_touch_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "archive"
            shutil.copytree(ROOT / "data" / "fiscal-flow" / "archive", archive)
            before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in archive.glob("*.json")}
            current_path = root / "current.json"
            manifest_path = root / "manifest.json"
            client_path = root / "fiscal-flow.json"
            api_rows = []
            current = self.client["current"]
            by_code = {item["line_code"]: item for item in current["receipts"] + current["positive_outlays"] + current["offsetting_outlays"]}
            by_code[120] = {"label": "Total", "amount_dollars": current["total_receipts_dollars"]}
            by_code[340] = {"label": "Total", "amount_dollars": current["net_outlays_dollars"]}
            for code, item in by_code.items():
                api_rows.append({"record_date": current["period_end"], "record_fiscal_year": str(current["fiscal_year"]), "classification_desc": item["label"], "current_fytd_rcpt_outly_amt": str(item["amount_dollars"]), "prior_fytd_rcpt_outly_amt": str(item["amount_dollars"]), "line_code_nbr": str(code), "data_type_cd": "D", "sequence_level_nbr": "2", "print_order_nbr": str(code)})
            client_manifest_path = root / "fiscal-flow-manifest.json"
            debt_path = root / "debt.json"
            debt_rows = [{"record_date": "2006-09-01", "tot_pub_debt_out_amt": "8500000000000"}, {"record_date": current["period_end"], "tot_pub_debt_out_amt": "40000000000000"}]
            with patch.multiple(fiscal_flow, ROOT=root, ARCHIVE=archive, CURRENT=current_path, DEBT=debt_path, MANIFEST=manifest_path, CLIENT=client_path, CLIENT_MANIFEST=client_manifest_path), patch.object(fiscal_flow, "api_rows", return_value=api_rows), patch.object(fiscal_flow, "debt_rows", return_value=debt_rows):
                fiscal_flow.run(argparse.Namespace(backfill=False, migrate_existing=False))
            after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in archive.glob("*.json")}
            self.assertEqual(before, after)
            self.assertTrue(current_path.exists())
            self.assertTrue(client_path.exists())
            self.assertTrue(client_manifest_path.exists())


class FiscalFlowUiContractTests(unittest.TestCase):
    def test_ui_has_required_markers(self):
        for relative_js, relative_css in [("src/app.js", "src/styles.css"), ("design-preview/src/app.js", "design-preview/theme.css")]:
            js = (ROOT / relative_js).read_text()
            css = (ROOT / relative_css).read_text()
            with self.subTest(js=relative_js):
                for marker in ["U.S. Fiscal Flow", "What changed now", "Frozen year", "context only", "excluded from the Bitcoin score", "Offsets / recoveries", "fiscalYearSelect", "Total public debt", "Debt to the Penny source"]:
                    self.assertIn(marker, js)
                self.assertIn("@media (max-width: 760px)", css)
                self.assertIn(".fiscal-sankey { grid-template-columns: 1fr", css)


if __name__ == "__main__":
    unittest.main()
