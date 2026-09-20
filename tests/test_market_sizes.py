import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('market_sizes', ROOT / 'scripts/market_sizes.py')
market_sizes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(market_sizes)


class MarketSizeTests(unittest.TestCase):
    def test_circulating_cap_not_fdv(self):
        row = market_sizes.crypto_record({'id': 'sui', 'market_cap': 123, 'fully_diluted_valuation': 999, 'last_updated': '2026-09-04T00:00:00Z'})
        self.assertEqual(row['value_usd'], 123)
        self.assertEqual(row['as_of'], '2026-09-04')

    def test_rejects_bad_values(self):
        for value in (None, 0, -1, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                market_sizes.positive(value)

    def test_gold_uses_tonnes_and_spot(self):
        record = market_sizes.metal_record({'stock_quantity': 1, 'stock_unit': 'tonnes', 'stock_as_of': '2025-12-31'}, {'price': 100, 'updatedAt': '2026-09-04T00:00:00Z', 'symbol': 'XAU'})
        self.assertAlmostEqual(record['value_usd'], 3215074.6568627)
        self.assertEqual(record['stock_as_of'], '2025-12-31')

    def test_silver_uses_all_form_stock_not_etf(self):
        seeds = json.loads((ROOT / 'data/manual/market-sizes.json').read_text())
        result = market_sizes.metal_record(seeds['silver'], {'price': 60, 'updatedAt': '2026-09-04T00:00:00Z', 'symbol': 'XAG'})
        self.assertEqual(result['value_usd'], 19300000000 * 60)
        self.assertEqual(result['stock_as_of'], '2023-12-31')

    def test_failed_refresh_retains_original_date(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sizes.json'
            path.write_text(json.dumps({'assets': {'btc': {'value_usd': 123, 'as_of': '2026-09-01'}}}))
            def failed(url):
                raise TimeoutError('offline')
            result = market_sizes.refresh_market_sizes(output=path, fetch=failed)
            self.assertEqual(result['assets']['btc']['value_usd'], 123)
            self.assertEqual(result['assets']['btc']['as_of'], '2026-09-01')
            self.assertIn('failed', result['assets']['btc']['status'])
            self.assertIsNone(result['assets']['silver']['value_usd'])

    def test_snapshot_has_all_assets_and_explicit_index_coverage(self):
        rows = json.loads((ROOT / 'public/data/market-sizes.json').read_text())['assets']
        assets = json.loads((ROOT / 'public/data/assets.json').read_text())['assets']
        self.assertEqual(set(rows), {a['id'] for a in assets})
        for row in rows.values():
            self.assertGreater(row['value_usd'], 0)
            self.assertTrue(row['source_url'].startswith('https://'))
        for key in ('sp500', 'nasdaq'):
            self.assertIn('coverage', rows[key]['method'])
            self.assertEqual(rows[key]['label'], 'Tracked cap*')
            self.assertIsNone(rows[key]['as_of'])


if __name__ == '__main__':
    unittest.main()
