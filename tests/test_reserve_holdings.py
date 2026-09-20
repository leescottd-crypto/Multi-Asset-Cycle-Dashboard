import json
import unittest
from scripts.reserve_holdings import ROOT, GOVERNMENTS, build, btc_rows, treasury_rows, treasury_history


class ReserveHoldingsTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'public/data/reserve-holdings.json').read_text())

    def test_shared_denominator_and_nonzero_gaps(self):
        rows = self.data['series']
        self.assertEqual(len(rows), len({r['date'] for r in rows}))
        self.assertEqual(rows, sorted(rows, key=lambda r:r['date']))
        for row in rows:
            for key in ['gold','treasuries','bitcoin']:
                if row[key+'_usd_m'] is not None:
                    self.assertAlmostEqual(row[key+'_pct'], row[key+'_usd_m']/row['reserves_usd_m']*100)
                else:
                    self.assertIsNone(row[key+'_pct'])
            if row['date'] < '2025-09-01':
                self.assertIsNone(row['bitcoin_pct'])

    def test_sources_and_coverage(self):
        self.assertEqual(self.data['government_coverage'], GOVERNMENTS)
        self.assertEqual(len(self.data['sources']),4)
        self.assertEqual(self.data['series'][0]['date'],'2000-03-31')
        self.assertEqual(len(self.data['series']),106)
        self.assertGreaterEqual(len(self.data['series']),12)
        self.assertGreaterEqual(sum(r['bitcoin_pct'] is not None for r in self.data['series']),2)
        self.assertIn('not part of',self.data['methodology'])

    def test_bad_inputs_fail_not_zero_fill(self):
        with self.assertRaises(ValueError):
            treasury_history(b'error page')
        with self.assertRaises((KeyError,ValueError)):
            btc_rows({'holdings': [], 'holding_value_in_usd': []})
        with self.assertRaises((StopIteration,ValueError)):
            treasury_rows(b'error page')
        with self.assertRaises(ValueError):
            build({'series':[]}, {}, {})

    def test_both_surfaces_use_shared_chart(self):
        for path in ['src/app.js','design-preview/src/app.js']:
            self.assertIn('mountReserveHoldings', (ROOT/path).read_text())
        for path in ['index.html','design-preview/index.html']:
            self.assertIn('reserve-holdings.css', (ROOT/path).read_text())
            self.assertIn('macroReservesPane', (ROOT/path).read_text())


if __name__ == '__main__':
    unittest.main()
