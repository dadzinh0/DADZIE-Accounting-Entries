import sys
import unittest
from pathlib import Path
from io import BytesIO
from openpyxl import load_workbook
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from batch_report import build_exception_report, verify_exception_report, exception_rows

class ReportTests(unittest.TestCase):
    def test_report_reopens_and_sanitizes_formula(self):
        items = [{'name':'=1+1', 'supplier':'+fictif', 'status':'review', 'issues':[{'code':'unverified_rule','severity':'critical','explanation':'Vérifier'}]}]
        data = build_exception_report(items)
        workbook = load_workbook(BytesIO(data))
        self.assertEqual(workbook['ANOMALIES']['A2'].value, "'=1+1")
        self.assertEqual(workbook['ANOMALIES']['B2'].value, "'+fictif")
        verify_exception_report(data, exception_rows(items))
        with self.assertRaises(ValueError): verify_exception_report(data, [])
    def test_empty_report(self):
        data = build_exception_report([])
        self.assertEqual(load_workbook(BytesIO(data)).sheetnames, ['ANOMALIES'])

if __name__ == '__main__': unittest.main()
