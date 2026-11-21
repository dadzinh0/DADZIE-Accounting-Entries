import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import fitz
from layout_extraction import extract_pdf
from extraction import validate_totals
from batch_validation import assess

class LayoutExtractionTests(unittest.TestCase):
    def test_unlabeled_logo_and_column_totals(self):
        pdf = fitz.open()
        page = pdf.new_page(width=595, height=842)
        page.insert_text((40, 180), 'FACTURE N° : FIC-2026-007')
        page.insert_text((40, 220), '12/08/26')
        page.insert_text((40, 260), 'CLIENT EXEMPLE')
        page.insert_text((40, 280), 'ICE : 000000000000001')
        page.insert_text((40, 740), 'RC N° : 12345 - ICE : 000000000000002')
        page.insert_text((225, 650), 'Total HT')
        page.insert_text((290, 650), '100,00')
        page.insert_text((225, 670), 'TVA 20%')
        page.insert_text((290, 670), '20,00')
        page.insert_text((490, 630), 'NET A PAYER')
        page.insert_text((500, 670), '120,00')
        with patch('layout_extraction.pytesseract.image_to_string', return_value='Compagnie Exemple Fictive\n'):
            fields = extract_pdf(pdf)
        self.assertEqual(fields['invoice_number']['value'], 'FIC-2026-007')
        self.assertEqual(fields['invoice_date']['value'], '12/08/2026')
        self.assertEqual(fields['ice']['value'], '000000000000002')
        self.assertEqual(fields['supplier']['origin'], 'ocr_uncertain')
        self.assertEqual(fields['amount_ht']['value'], '100.00')
        self.assertEqual(fields['vat_amount']['value'], '20.00')
        self.assertEqual(fields['amount_ttc']['value'], '120.00')
        self.assertEqual(validate_totals(fields), 'consistent')
        self.assertIn('uncertain_supplier', [issue['code'] for issue in assess(fields)['issues']])

if __name__ == '__main__': unittest.main()
