"""Build and independently reopen an exception-only batch report."""
from io import BytesIO
from openpyxl import Workbook, load_workbook

HEADERS = ('Fichier', 'Fournisseur', 'Référence', 'HT', 'TVA', 'TTC', 'Statut', 'Code', 'Sévérité', 'Explication')

def safe(value):
    text = str(value or '')
    if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')):
        return "'" + text
    return text

def exception_rows(items):
    return [tuple(safe(x) for x in (item['name'], item.get('supplier'), item.get('invoice_number'), item.get('amount_ht'), item.get('vat_amount'), item.get('amount_ttc'), item['status'], issue['code'], issue['severity'], issue['explanation'])) for item in items for issue in item['issues']]

def build_exception_report(items):
    rows = exception_rows(items)
    book = Workbook(); sheet = book.active; sheet.title = 'ANOMALIES'
    sheet.append(HEADERS)
    for row in rows: sheet.append(row)
    stream = BytesIO(); book.save(stream)
    data = stream.getvalue()
    verify_exception_report(data, rows)
    return data

def verify_exception_report(data, expected_rows):
    book = load_workbook(BytesIO(data), data_only=False)
    if book.sheetnames != ['ANOMALIES']: raise ValueError('Structure incorrecte')
    sheet = book['ANOMALIES']
    if sheet.max_row != len(expected_rows) + 1 or sheet.max_column != len(HEADERS): raise ValueError('Nombre de lignes incorrect')
    if tuple(c.value for c in sheet[1]) != HEADERS: raise ValueError('En-têtes incorrects')
    actual = [tuple(cell.value or '' for cell in row) for row in sheet.iter_rows(min_row=2)]
    if actual != expected_rows: raise ValueError('Anomalies incohérentes')
    if any(cell.data_type == 'f' for row in sheet for cell in row): raise ValueError('Formule inattendue')
