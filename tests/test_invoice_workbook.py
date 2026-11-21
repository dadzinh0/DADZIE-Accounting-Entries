import sys
import unittest
from io import BytesIO
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from openpyxl import load_workbook
from extraction import extract, validate_totals
from invoice_workbook import build_invoice_workbook, expected_rows, verify_invoice_workbook

SAMPLE = '''FACTURE
FOURNISSEUR (FICTIF)
ATLAS FOURNITURES INDUSTRIELLES (FICTIF)
ICE fictif : 000000000000001
N° FACTURE
DATE
ÉCHÉANCE
AFI-2026-0017
05/11/2026
05/12/2026
DÉSIGNATION
QTÉ
PU (MAD)
HT (MAD)
Câble électrique BT - rouleau
2
450,00
900,00
Total HT :
900,00 MAD
TVA (20 %) :
180,00 MAD
TOTAL TTC :1 080,00 MAD'''

class InvoiceWorkbookTests(unittest.TestCase):
    def test_scanned_layout_incorrect_total(self):
        text = '''FOURNISSEUR (FICTIF)
MARRAKECH APPROVISIONNEMENT (FICTIF)
N° FACTURE DATE
MA-2026-0099 14/11/2026
ÉCHÉANCE
29/11/2026
DÉSIGNATION
Équipement de protection - lot
QTÉ PU(MAD) HT (MAD)
4 250,00 1 000,00
Total HT 1 000,00 MAD
TVA (20 %) 200,00 MAD
TOTAL TTC :1 250,00 MAD'''
        fields = extract(text)
        self.assertEqual(fields['invoice_number']['value'], 'MA-2026-0099')
        self.assertEqual(fields['amount_ht']['value'], '1000.00')
        self.assertEqual(fields['vat_amount']['value'], '200.00')
        self.assertEqual(validate_totals(fields), 'inconsistent')

    def test_realistic_pdf_layout_extracts_detail(self):
        fields = extract(SAMPLE)
        self.assertEqual(fields['supplier']['value'], 'ATLAS FOURNITURES INDUSTRIELLES (FICTIF)')
        self.assertEqual(fields['invoice_number']['value'], 'AFI-2026-0017')
        self.assertEqual(fields['invoice_date']['value'], '05/11/2026')
        self.assertEqual(fields['vat_amount']['value'], '180.00')
        self.assertEqual(fields['currency']['value'], 'MAD')
        self.assertEqual(fields['lines']['value'][0]['description'], 'Câble électrique BT - rouleau')
        self.assertEqual(validate_totals(fields), 'consistent')

    def test_missing_reference_is_blank_and_flagged(self):
        fields = extract(SAMPLE.replace('AFI-2026-0017\n', ''))
        self.assertNotIn('invoice_number', fields)
        item = {'name':'missing.pdf','document_id':'test-id','status':'review','fields':fields,'totals':'consistent','issues':[{'code':'missing_invoice_number','severity':'critical','explanation':'Référence absente'}]}
        data = build_invoice_workbook([item])
        book = load_workbook(BytesIO(data))
        self.assertNotIn('État comptable', [cell.value for cell in book['FACTURES'][1]])
        self.assertIsNone(book['FACTURES']['E2'].value)
        self.assertEqual(book['FACTURES']['M2'].value, 'À vérifier')
        self.assertEqual(book['ANOMALIES']['C2'].value, 'missing_invoice_number')
        self.assertIn('Référence absente', book['FACTURES']['E2'].comment.text)
        self.assertEqual(book['FACTURES']['E2'].fill.fgColor.rgb[-6:], 'F4CCCC')

    def test_duplicate_still_exports_invoice_fields(self):
        fields = extract(SAMPLE)
        item = {'name':'=unsafe.pdf','document_id':'test-id','status':'review','fields':fields,'totals':'consistent','issues':[{'code':'duplicate_file','severity':'warning','explanation':'Doublon antérieur'}]}
        data = build_invoice_workbook([item])
        book = load_workbook(BytesIO(data))
        self.assertEqual(book['FACTURES']['A2'].value, "'=unsafe.pdf")
        self.assertEqual(book['FACTURES']['C2'].value, fields['supplier']['value'])
        self.assertEqual(book['FACTURES']['N2'].value, 'Oui')
        self.assertIn('Doublon antérieur', book['FACTURES']['N2'].comment.text)
        self.assertEqual(book['FACTURES']['M2'].value, 'Extrait')
        self.assertEqual(book['LIGNES']['C2'].value, 'Câble électrique BT - rouleau')
        with self.assertRaises(ValueError): verify_invoice_workbook(data, ([], [], []))

    def test_incorrect_totals_highlight_amount_cells(self):
        fields = extract(SAMPLE.replace('1 080,00 MAD', '1 090,00 MAD'))
        item = {'name':'incorrect.pdf','document_id':'test-id','status':'review','fields':fields,'totals':'inconsistent','issues':[{'code':'totals_inconsistent','severity':'critical','explanation':'HT + TVA ne correspond pas au TTC'}]}
        book = load_workbook(BytesIO(build_invoice_workbook([item])))
        for column in ('I','J','K','L'):
            cell = book['FACTURES'][f'{column}2']
            self.assertIn('HT + TVA', cell.comment.text)
            self.assertEqual(cell.fill.fgColor.rgb[-6:], 'F4CCCC')

if __name__ == '__main__': unittest.main()
