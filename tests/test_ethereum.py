import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EthereumTests(unittest.TestCase):
    def test_ethereum_uses_complete_shared_chart_payload(self):
        index = json.loads((ROOT / 'public/data/assets.json').read_text())['assets']
        self.assertEqual([a['id'] for a in index[:2]], ['btc', 'eth'])
        eth = json.loads((ROOT / 'public/data/eth.json').read_text())
        self.assertEqual(eth['asset']['symbol'], 'ETH-USD')
        self.assertGreater(len(eth['points']), 3000)
        for key in ('close', 'ma_50d', 'ma_100d', 'ma_200d', 'ma_200w', 'trend'):
            self.assertGreater(eth['latest'][key], 0)
        self.assertTrue(eth['rainbow'])
        self.assertTrue(eth['elliott_wave'])
        self.assertIn('Coinbase', eth['source']['source'])
        sizes = json.loads((ROOT / 'public/data/market-sizes.json').read_text())
        self.assertGreater(sizes['assets']['eth']['value_usd'], 0)


if __name__ == '__main__':
    unittest.main()
