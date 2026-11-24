"""Verify the structured policy against the unchanged approved TypeScript source."""
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Independent frozen mapping, in approved policy order, not read from the JSON.
STABLE_IDS = (
    'adult', 'gambling', 'drugs', 'dating', 'mixed', 'violence', 'piracy',
    'malware', 'anonymous', 'selfharm', 'hacking', 'messaging', 'mail',
    'bypass', 'social', 'video', 'gaming', 'music', 'shopping', 'news',
    'ai', 'sports', 'browsers', 'crypto', 'cloud', 'ads', 'live', 'remote',
)
FIELDS = ('name', 'definition', 'yes', 'no', 'rules')

class PolicyFidelityTests(unittest.TestCase):
    def test_all_28_categories_match_approved_source(self):
        source_path = ROOT / 'docs/approved-policy-v1.0.ts'
        checksum = (ROOT / 'docs/policy-sha256.txt').read_text().split()[0]
        self.assertEqual(hashlib.sha256(source_path.read_bytes()).hexdigest(), checksum)
        source = source_path.read_text()
        rows = []
        for line in source.splitlines():
            if not line.startswith('{n:'):
                continue
            ordinal = int(re.search(r'\{n:(\d+),', line).group(1))
            row = {'n': ordinal, 'id': STABLE_IDS[ordinal - 1]}
            for field in FIELDS:
                value = re.search(field + r":'((?:\\.|[^'])*)'", line)
                self.assertIsNotNone(value, (ordinal, field))
                row[field] = value.group(1).replace("\\'", "'")
            rows.append(row)
        self.assertEqual([r['n'] for r in rows], list(range(1, 29)))
        fixture = json.loads((ROOT / 'fixtures/policy-v1.0.json').read_text())
        self.assertEqual(fixture['version'], '1.0')
        self.assertEqual(len(fixture['categories']), 28)
        self.assertEqual([c['id'] for c in fixture['categories']], list(STABLE_IDS))
        for expected, actual in zip(rows, fixture['categories']):
            for field in ('n', 'id', *FIELDS):
                with self.subTest(category=expected['n'], field=field):
                    self.assertEqual(actual[field], expected[field])

if __name__ == '__main__':
    unittest.main(verbosity=2)
