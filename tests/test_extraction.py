import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from extraction import extract, validate_totals

class ExtractionTests(unittest.TestCase):
    def test_synthetic_invoice(self):
        fields = extract('Fournisseur: Société fictive\nFacture N°: TEST-01\nDate: 01/11/2026\nDevise: MAD\nHT: 1000,00\nTVA: 200,00\nTTC: 1200,00')
        self.assertEqual(fields['invoice_number']['value'], 'TEST-01')
        self.assertEqual(validate_totals(fields), 'consistent')
        self.assertEqual(fields['amount_ht']['origin'], 'extracted')
    def test_inconsistent_and_missing(self):
        fields = extract('HT: 100,00\nTVA: 20,00\nTTC: 121,00')
        self.assertEqual(validate_totals(fields), 'inconsistent')
        self.assertEqual(validate_totals(extract('Facture N°: TEST')), 'missing')
    def test_invalid_values_are_not_validated(self):
        fields = {k: {'value': 'NaN'} for k in ('amount_ht', 'vat_amount', 'amount_ttc')}
        self.assertEqual(validate_totals(fields), 'invalid')
    def test_does_not_invent_fields(self):
        self.assertEqual(extract('Texte sans données'), {})

if __name__ == '__main__': unittest.main()
