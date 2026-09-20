import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PolicyAdoptionTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'public/data/policy-adoption.json').read_text())

    def test_status_and_impact_are_separate(self):
        self.assertEqual([card['key'] for card in self.data['cards']], ['central_banks', 'clarity', 'us_reserve'])
        self.assertTrue(all(card['impact'] in {'supportive', 'restrictive', 'neutral'} for card in self.data['cards']))
        self.assertIn('not a Federal Reserve', self.data['cards'][2]['note'])

    def test_sources_are_primary_and_resolve(self):
        sources = {source['id']: source for source in self.data['sources']}
        self.assertGreaterEqual(len(self.data['events']), 8)
        self.assertTrue(all(event['source_id'] in sources for event in self.data['events']))
        self.assertTrue(all(bank['source_id'] in sources for bank in self.data['central_banks']))
        self.assertTrue(all(source['url'].startswith('https://') for source in sources.values()))

    def test_legislative_tracker_does_not_claim_enactment(self):
        stages = {stage['label']: stage for stage in self.data['clarity_stages']}
        self.assertEqual(stages['Senate reported']['state'], 'complete')
        self.assertEqual(stages['Enacted']['state'], 'pending')

    def test_arma_tracker_only_completes_verified_milestones(self):
        tracker = self.data['arma_tracker']
        self.assertIn('H.R. 8957', tracker['bill'])
        complete = [stage for stage in tracker['stages'] if stage['state'] == 'complete']
        self.assertEqual([stage['label'] for stage in complete], ['Introduced', 'House referral'])
        self.assertTrue(all(stage['date'] == '2026-05-21' for stage in complete))
        pending = [stage for stage in tracker['stages'] if stage['state'] == 'pending']
        self.assertEqual(len(pending), 4)
        self.assertTrue(all(stage['date'] is None for stage in pending))
        self.assertIn('not an enacted law', tracker['summary'])
        self.assertIn('could not be accessed', tracker['verification_note'])
        self.assertTrue(tracker['source_url'].startswith('https://www.govinfo.gov/'))
        self.assertIn('renderArmaTracker(data.arma_tracker)', (ROOT / 'src/policy-adoption.js').read_text())

    def test_both_dashboard_surfaces_are_wired(self):
        for path in ['src/app.js', 'design-preview/src/app.js']:
            text = (ROOT / path).read_text()
            self.assertIn('mountPolicyAdoption', text)
            self.assertIn("policy: 'macroPolicyPane'", text)
        for path in ['index.html', 'design-preview/index.html']:
            text = (ROOT / path).read_text()
            self.assertIn('policy-adoption.css', text)
            self.assertIn('data-macro-tab="policy"', text)
            self.assertIn('macroPolicyPane', text)


if __name__ == '__main__':
    unittest.main()
