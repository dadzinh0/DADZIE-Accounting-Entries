"""Invoice data export, separate from unapproved accounting entries."""
from io import BytesIO
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment
from openpyxl.styles import PatternFill
from batch_report import safe

SHEETS = ('FACTURES', 'LIGNES', 'ANOMALIES')
INVOICE_HEADERS = ('Fichier', 'Document ID', 'Fournisseur', 'ICE', 'Référence facture', 'Date facture', 'Échéance', 'Devise', 'Total HT', 'TVA', 'Total TTC', 'Contrôle montants', 'État extraction', 'Doublon')
LINE_HEADERS = ('Document ID', 'Référence facture', 'Description', 'Quantité', 'Prix unitaire', 'Montant HT', 'Origine')
ISSUE_HEADERS = ('Document ID', 'Fichier', 'Code', 'Sévérité', 'Explication')
HIGHLIGHTS = {'missing':'F4CCCC', 'warning':'F4CCCC', 'critical':'F4CCCC'}
FIELD_COLUMNS = {'supplier':'C', 'ice':'D', 'invoice_number':'E', 'invoice_date':'F',
    'due_date':'G', 'currency':'H', 'amount_ht':'I', 'vat_amount':'J', 'amount_ttc':'K'}

def _targets(issue):
    code = issue.get('code', '')
    if code in ('duplicate_file',): return ('N',), 'warning'
    if code == 'duplicate_reference': return ('E',), 'warning'
    if code.startswith('missing_'):
        return (FIELD_COLUMNS.get(code[8:], 'M'),), 'missing'
    if code.startswith('totals_'):
        return ('I', 'J', 'K', 'L'), 'critical'
    if code == 'unsupported_currency': return ('H',), 'warning'
    if code == 'uncertain_supplier': return ('C',), 'warning'
    if code == 'model_suggestion_review':
        return tuple(FIELD_COLUMNS[key] for key in issue.get('fields', []) if key in FIELD_COLUMNS) or ('M',), 'warning'
    if code == 'calculated_total_review':
        return tuple(FIELD_COLUMNS[key] for key in issue.get('fields', []) if key in FIELD_COLUMNS) or ('M',), 'warning'
    if code in ('processing_failed', 'report_extraction_failed'): return ('A', 'M'), 'critical'
    if code == 'unverified_rule': return (), 'warning'
    return ('M',), 'warning'

def _annotate(sheet, items):
    for row_index, item in enumerate(items, 2):
        for issue in item.get('issues', []):
            columns, level = _targets(issue)
            for column in columns:
                cell = sheet[f'{column}{row_index}']
                message = str(issue.get('explanation') or issue.get('code') or 'À vérifier')
                previous = cell.comment.text + '\n' if cell.comment else ''
                cell.comment = Comment(previous + message, 'PROHEAT')
                if level == 'critical' or not cell.fill.patternType:
                    cell.fill = PatternFill('solid', fgColor=HIGHLIGHTS[level])

def _field(fields, key):
    return (fields.get(key) or {}).get('value')

def _amount(value):
    try:
        return Decimal(str(value)) if value not in (None, '') else None
    except InvalidOperation:
        return None

def _date(value):
    try:
        return datetime.strptime(str(value), '%d/%m/%Y').date() if value else None
    except ValueError:
        return None

def expected_rows(items):
    invoices, lines, issues = [], [], []
    for item in items:
        fields = item.get('fields') or {}
        codes = [issue.get('code', '') for issue in item.get('issues', [])]
        extraction_issues = [c for c in codes if c != 'unverified_rule' and c != 'duplicate_file']
        status = 'Échec' if item['status'] == 'failed' else ('À vérifier' if extraction_issues else 'Extrait')
        totals = item.get('totals') or ''
        invoices.append((safe(item['name']), safe(item.get('document_id')), safe(_field(fields, 'supplier')),
            safe(_field(fields, 'ice')), safe(_field(fields, 'invoice_number')),
            _date(_field(fields, 'invoice_date')), _date(_field(fields, 'due_date')),
            safe(_field(fields, 'currency')), _amount(_field(fields, 'amount_ht')),
            _amount(_field(fields, 'vat_amount')), _amount(_field(fields, 'amount_ttc')),
            safe(totals), safe(status), 'Oui' if 'duplicate_file' in codes else 'Non'))
        for line in _field(fields, 'lines') or []:
            lines.append((safe(item.get('document_id')), safe(_field(fields, 'invoice_number')),
                safe(line.get('description')), _amount(line.get('quantity')),
                _amount(line.get('unit_price')), _amount(line.get('amount_ht')), safe(line.get('origin'))))
        for issue in item.get('issues', []):
            if issue.get('code') in ('duplicate_file', 'unverified_rule'):
                continue
            issues.append(tuple(safe(v) for v in (item.get('document_id'), item['name'], issue.get('code'), issue.get('severity'), issue.get('explanation'))))
    return invoices, lines, issues

def build_invoice_workbook(items):
    rows = expected_rows(items)
    book = Workbook(); book.remove(book.active)
    for name, headers, records in zip(SHEETS, (INVOICE_HEADERS, LINE_HEADERS, ISSUE_HEADERS), rows):
        sheet = book.create_sheet(name); sheet.append(headers)
        sheet.freeze_panes = 'A2'; sheet.auto_filter.ref = f'A1:{get_column_letter(len(headers))}{max(1, len(records)+1)}'
        for record in records: sheet.append(record)
        if name == 'FACTURES':
            for row in sheet.iter_rows(min_row=2):
                for cell in row[5:7]: cell.number_format = 'dd/mm/yyyy'
                for cell in row[8:11]: cell.number_format = '#,##0.00'
            _annotate(sheet, items)
        elif name == 'LIGNES':
            for row in sheet.iter_rows(min_row=2):
                for cell in row[3:6]: cell.number_format = '#,##0.00'
        for column in sheet.columns:
            letter = column[0].column_letter
            sheet.column_dimensions[letter].width = min(54, max(12, max(len(str(c.value or '')) for c in column) + 2))
    out = BytesIO(); book.save(out); data = out.getvalue()
    verify_invoice_workbook(data, rows, items)
    return data

def verify_invoice_workbook(data, rows, items=None):
    book = load_workbook(BytesIO(data), data_only=False)
    if tuple(book.sheetnames) != SHEETS: raise ValueError('Structure de classeur incorrecte')
    for name, headers, expected in zip(SHEETS, (INVOICE_HEADERS, LINE_HEADERS, ISSUE_HEADERS), rows):
        sheet = book[name]
        if tuple(c.value for c in sheet[1]) != headers: raise ValueError('En-têtes incorrects : ' + name)
        actual = [tuple(c.value for c in row) for row in sheet.iter_rows(min_row=2)]
        if len(actual) != len(expected): raise ValueError('Nombre de lignes incorrect : ' + name)
        for observed, source in zip(actual, expected):
            for value, original in zip(observed, source):
                if isinstance(original, Decimal):
                    if value is None or Decimal(str(value)) != original: raise ValueError('Montant incorrect : ' + name)
                elif isinstance(original, date):
                    if not isinstance(value, datetime) or value.date() != original: raise ValueError('Date incorrecte : ' + name)
                elif (value or '') != (original or ''):
                    raise ValueError('Données différentes après réouverture : ' + name)
        if any(c.data_type == 'f' for row in sheet for c in row): raise ValueError('Formule inattendue')
    if items is not None:
        sheet = book['FACTURES']
        for row_index, item in enumerate(items, 2):
            for issue in item.get('issues', []):
                columns, _ = _targets(issue)
                for column in columns:
                    cell = sheet[f'{column}{row_index}']
                    if not cell.comment or not cell.fill.patternType:
                        raise ValueError('Annotation manquante : ' + cell.coordinate)
