"""Conservative local extraction. Unmatched values are never fabricated."""
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MONEY = r'(?<![\d.,])(-?(?:\d{1,3}(?:[., \u00a0\u202f]\d{3})+|\d+)[.,]\d{2,3})(?![\d.,])'


def normalize_amount(raw):
    whole, fraction = re.split(r'[.,](?=\d{2,3}$)', raw.strip())
    return re.sub(r'[.,\s]', '', whole) + '.' + fraction


def extract(text):
    money = MONEY
    patterns = {
        'supplier': r'(?im)^\s*(?:fournisseur|supplier)\s*:\s*(.+)$',
        'invoice_number': r'(?im)^[ \t]*(?:facture[ \t]*(?:n[°o]|numéro)|invoice[ \t]*(?:no|number))(?:[ \t]*[:#][ \t]*|[ \t]+)(?=[^\r\n]*\d)([A-Z0-9][A-Z0-9/-]*)',
        'invoice_date': r'(?im)^\s*(?:date(?: de facture)?)\s*:\s*(\d{2}[/-]\d{2}[/-]\d{4})',
        'ice': r'(?im)^\s*ICE\s*:\s*([0-9]{15})',
        'currency': r'(?im)^\s*(?:devise|currency)\s*:\s*(MAD|EUR|USD)\b',
        'amount_ht': r'(?im)^\s*(?:(?:total\s*)?H\.?\s*T\.?|subtotal)\s*:?\s*' + money,
        'vat_amount': r'(?im)^\s*(?:montant\s*)?(?:TVA|VAT)(?:\s*\(?\s*\d+(?:[,.]\d+)?\s*%\s*\)?)?\s*:?\s*' + money,
        'amount_ttc': r'(?im)^\s*(?:(?:total\s*)?TTC|grand total|net\s+[àa]\s+payer)\s*:?\s*' + money,
    }
    result = {}
    for name, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip()
            if name in ('amount_ht', 'vat_amount', 'amount_ttc'):
                value = normalize_amount(value)
            result[name] = {'value': value, 'origin': 'extracted', 'evidence': match.group(0).strip()}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    def put(name, value, evidence):
        if value and name not in result:
            result[name] = {'value': value, 'origin': 'extracted', 'evidence': evidence}
    money = MONEY
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
        for name, label in (('amount_ht', r'(?:Total\s+H\.?\s*T\.?|H\.?\s*T\.?\s*:)'), ('vat_amount', r'TVA(?:\s+\d+(?:[,.]\d+)?\s*%|\s*\([^)]*\))?'), ('amount_ttc', r'(?:TOTAL\s+TTC|NET\s+[àa]\s+PAYER)')):
            if re.search(r'(?i)\b(?:DÉSIGNATION|QUANTITÉ|PRIX\s+U)\b', line):
                continue
            match = re.search(label + r'\s*:?[ \t]*' + money, line, re.I)
            if match: put(name, normalize_amount(match.group(1)), line)
        if 'amount_ttc' not in result and re.search(r'NET\s+[àa]\s+PAYER', line, re.I):
            for candidate in lines[index + 1:index + 5]:
                if re.search(r'\b(?:HT|TVA|BASES?)\b', candidate, re.I):
                    continue
                match = re.fullmatch(r'\s*' + money + r'\s*', candidate, re.I)
                if match:
                    put('amount_ttc', normalize_amount(match.group(1)), line + ' / ' + candidate)
                    break
        if 'amount_ttc' not in result and re.search(r'(?i)arr[êe]t[ée]e?\b.*\bsomme\s+de', line):
            for candidate in [line] + lines[index + 1:index + 4]:
                if re.search(r'(?i)\b(?:TVA|TOTAL\s+HT|H\.?\s*T\.?)\b', candidate):
                    continue
                amounts = list(re.finditer(money, candidate))
                if amounts:
                    chosen = normalize_amount(amounts[-1].group(1))
                    put('amount_ttc', chosen, line + ' / ' + candidate)
                    break
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

def derive_missing_totals(fields, source_text):
    """Derive missing HT/VAT only from a TTC and one explicit invoice VAT rate."""
    rate_matches = re.findall(
        r'(?i)\bTVA\s*(?:\(?\s*)(\d{1,2}(?:[,.]\d+)?)\s*%',
        source_text or '',
    )
    rates = set()
    for raw_rate in rate_matches:
        try:
            rate = Decimal(raw_rate.replace(',', '.'))
        except InvalidOperation:
            continue
        if rate.is_finite() and Decimal('0') <= rate <= Decimal('100'):
            rates.add(rate)
    if len(rates) != 1:
        return fields

    ttc_field = fields.get('amount_ttc') or {}
    try:
        ttc = Decimal(str(ttc_field.get('value')))
        if not ttc.is_finite() or ttc < 0:
            return fields
    except (InvalidOperation, TypeError):
        return fields

    ht_field = fields.get('amount_ht') or {}
    vat_field = fields.get('vat_amount') or {}
    ht_exists = bool(ht_field.get('value'))
    vat_exists = bool(vat_field.get('value'))
    if ht_exists and vat_exists:
        return fields

    rate = next(iter(rates)) / Decimal('100')
    decimals = [len(str(field.get('value')).partition('.')[2])
                for field in (ttc_field, ht_field, vat_field)
                if field.get('value') and '.' in str(field.get('value'))]
    precision = max(2, min(3, max(decimals, default=2)))
    quantum = Decimal('1').scaleb(-precision)
    evidence = 'Calcul depuis Total TTC et le taux de TVA explicite (' + str(next(iter(rates))) + '%)'

    try:
        if not ht_exists and not vat_exists:
            ht = (ttc / (Decimal('1') + rate)).quantize(quantum, rounding=ROUND_HALF_UP)
            vat = ttc - ht
        elif ht_exists:
            ht = Decimal(str(ht_field['value']))
            vat = ttc - ht
        else:
            vat = Decimal(str(vat_field['value']))
            ht = ttc - vat
        expected_vat = (ht * rate).quantize(quantum, rounding=ROUND_HALF_UP)
        if ht < 0 or vat < 0 or vat != expected_vat or ht + vat != ttc:
            return fields
    except (InvalidOperation, KeyError, TypeError, ValueError):
        return fields

    if not ht_exists:
        fields['amount_ht'] = {
            'value': format(ht, f'.{precision}f'),
            'origin': 'calculated',
            'evidence': evidence,
        }
    if not vat_exists:
        fields['vat_amount'] = {
            'value': format(vat, f'.{precision}f'),
            'origin': 'calculated',
            'evidence': evidence,
        }
    return fields

def validate_totals(fields):
    try:
        vals = [Decimal(fields[k]['value']) for k in ('amount_ht', 'vat_amount', 'amount_ttc')]
        if not all(v.is_finite() and v >= 0 for v in vals):
            return 'invalid'
        return 'consistent' if vals[0] + vals[1] == vals[2] else 'inconsistent'
    except (KeyError, InvalidOperation, TypeError):
        return 'missing'
