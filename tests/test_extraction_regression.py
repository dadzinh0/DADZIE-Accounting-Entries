import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from extraction import extract, validate_totals

class ExtractionRegression(unittest.TestCase):
    def test_missing_reference_does_not_consume_next_line(self):
        fields = extract('Fournisseur: Fictif\nFacture No:\nDate: 01/11/2026\n')
        self.assertNotIn('invoice_number', fields)

    def test_inconsistent_totals_from_ocr_text(self):
        fields = extract('Fournisseur: Fictif\nFacture No: X1\nHT: 100,00\nTVA: 20,00\nTTC: 121,00')
        self.assertEqual(validate_totals(fields), 'inconsistent')
