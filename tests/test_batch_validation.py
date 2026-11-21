import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from extraction import extract
from batch_validation import assess

class BatchValidationTests(unittest.TestCase):
    def test_consistent_invoice_still_requires_verified_rule(self):
        fields = extract('Fournisseur: Exemple fictif\nFacture No: TEST-01\nDate: 01/11/2026\nDevise: MAD\nHT: 100,00\nTVA: 20,00\nTTC: 120,00')
        result = assess(fields)
        self.assertFalse(result['eligible_for_export'])
        self.assertEqual([x['code'] for x in result['issues']], ['unverified_rule'])
    def test_missing_duplicate_and_unsupported(self):
        fields = extract('Fournisseur: Exemple fictif\nFacture No: TEST-01\nDevise: EUR')
        codes = {x['code'] for x in assess(fields, {('exemple fictif', 'test-01')})['issues']}
        self.assertTrue({'missing_invoice_date', 'unsupported_currency', 'duplicate_reference', 'unverified_rule'} <= codes)

if __name__ == '__main__': unittest.main()
