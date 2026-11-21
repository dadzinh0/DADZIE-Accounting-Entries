"""Conservative local extraction. Unmatched values are never fabricated."""
import re
from decimal import Decimal, InvalidOperation

def extract(text):
    patterns = {
        'supplier': r'(?im)^\s*(?:fournisseur|supplier)\s*:\s*(.+)$',
        'invoice_number': r'(?im)^[ \t]*(?:facture[ \t]*(?:n[°o]|numéro)|invoice[ \t]*(?:no|number))(?:[ \t]*[:#][ \t]*|[ \t]+)([^\s:#\r\n][^\r\n]*)$',
        'invoice_date': r'(?im)^\s*(?:date(?: de facture)?)\s*:\s*(\d{2}[/-]\d{2}[/-]\d{4})',
        'ice': r'(?im)^\s*ICE\s*:\s*([0-9]{15})',
        'currency': r'(?im)^\s*(?:devise|currency)\s*:\s*(MAD|EUR|USD)\b',
        'amount_ht': r'(?im)^\s*(?:total\s*)?HT\s*:\s*([\d ]+[,.]\d{2})',
        'vat_amount': r'(?im)^\s*(?:montant\s*)?TVA\s*:\s*([\d ]+[,.]\d{2})',
        'amount_ttc': r'(?im)^\s*(?:total\s*)?TTC\s*:\s*([\d ]+[,.]\d{2})',
    }
    result = {}
    for name, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip()
            if name in ('amount_ht', 'vat_amount', 'amount_ttc'):
                value = value.replace(' ', '').replace(',', '.')
            result[name] = {'value': value, 'origin': 'extracted', 'evidence': match.group(0).strip()}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    def put(name, value, evidence):
        if value and name not in result:
            result[name] = {'value': value, 'origin': 'extracted', 'evidence': evidence}
    money = r'(\d[\d\s]*[,.]\d{2})'
    for index, line in enumerate(lines):
        following = lines[index + 1] if index + 1 < len(lines) else ''
        if re.fullmatch(r'FOURNISSEUR\s*\(FICTIF\)', line, re.I):
            put('supplier', following, line + ' / ' + following)
        if re.match(r'^ICE\s*(?:fictif)?\s*:', line, re.I):
            match = re.search(r'(\d{15})', line)
            if match: put('ice', match.group(1), line)
        if re.fullmatch(r'N[°o]\s*FACTURE', line, re.I):
            candidate = lines[index + 3] if index + 3 < len(lines) else ''
            if re.fullmatch(r'[A-Za-z][A-Za-z0-9/-]{2,}', candidate):
                put('invoice_number', candidate, line + ' / ' + candidate)
        if re.fullmatch(r'N[°o]\s*FACTURE\s+DATE', line, re.I):
            match = re.match(r'([A-Za-z][A-Za-z0-9/-]{2,})\s+(\d{2}/\d{2}/\d{4})', following)
            if match:
                put('invoice_number', match.group(1), line + ' / ' + following)
                put('invoice_date', match.group(2), line + ' / ' + following)
        if re.fullmatch(r'ÉCHÉANCE', line, re.I) and re.fullmatch(r'\d{2}/\d{2}/\d{4}', following):
            put('due_date', following, line + ' / ' + following)
        if line.upper() == 'DATE' and index + 2 < len(lines) and lines[index + 1].upper().startswith('ÉCHÉANCE'):
            dates = [candidate for candidate in lines[index + 2:index + 5] if re.fullmatch(r'\d{2}/\d{2}/\d{4}', candidate)]
            if dates: put('invoice_date', dates[0], line + ' / ' + dates[0])
            if len(dates) > 1: put('due_date', dates[1], lines[index + 1] + ' / ' + dates[1])
        for name, label in (('amount_ht', r'Total\s+HT'), ('vat_amount', r'TVA(?:\s*\([^)]*\))?'), ('amount_ttc', r'TOTAL\s+TTC')):
            match = re.match(r'^' + label + r'\s*:?[ \t]*' + money, line, re.I)
            if match: put(name, match.group(1).replace(' ', '').replace(',', '.'), line)
            elif re.fullmatch(label + r'\s*:', line, re.I):
                match = re.match(money, following)
                if match: put(name, match.group(1).replace(' ', '').replace(',', '.'), line + ' / ' + following)
        if 'MAD' in line.upper() and ('PU (' in line.upper() or 'TOTAL' in line.upper()):
            put('currency', 'MAD', line)
        if re.match(r'^DÉSIGNATION$', line, re.I) and index + 3 < len(lines):
            details = []
            cursor = index + 4
            while cursor + 3 < len(lines) and not re.match(r'^Total\s+HT', lines[cursor], re.I):
                label, quantity, unit, amount = lines[cursor:cursor + 4]
                if not re.fullmatch(r'\d+(?:[,.]\d+)?', quantity) or not re.fullmatch(money, unit) or not re.fullmatch(money, amount): break
                details.append({'description':label, 'quantity':quantity.replace(',', '.'), 'unit_price':unit.replace(' ', '').replace(',', '.'), 'amount_ht':amount.replace(' ', '').replace(',', '.'), 'origin':'extracted'})
                cursor += 4
            if details: result['lines'] = {'value':details, 'origin':'extracted', 'evidence':'DÉSIGNATION / QTÉ / PU / HT'}
            elif index + 1 < len(lines) and not lines[index + 1].upper().startswith('FICTIF'):
                # OCR may separate the description from the numeric columns.
                description = lines[index + 1]
                for candidate in lines[index + 2:index + 15]:
                    numeric = re.fullmatch(r'(\d+)\s+' + money + r'\s+' + money, candidate)
                    if numeric:
                        result['lines'] = {'value':[{'description':description, 'quantity':numeric.group(1), 'unit_price':numeric.group(2).replace(' ', '').replace(',', '.'), 'amount_ht':numeric.group(3).replace(' ', '').replace(',', '.'), 'origin':'extracted'}], 'origin':'extracted', 'evidence':description + ' / ' + candidate}
                        break
    return result

def validate_totals(fields):
    try:
        vals = [Decimal(fields[k]['value']) for k in ('amount_ht', 'vat_amount', 'amount_ttc')]
        if not all(v.is_finite() and v >= 0 for v in vals):
            return 'invalid'
        return 'consistent' if vals[0] + vals[1] == vals[2] else 'inconsistent'
    except (KeyError, InvalidOperation, TypeError):
        return 'missing'
