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
    return result

def validate_totals(fields):
    try:
        vals = [Decimal(fields[k]['value']) for k in ('amount_ht', 'vat_amount', 'amount_ttc')]
        if not all(v.is_finite() and v >= 0 for v in vals):
            return 'invalid'
        return 'consistent' if vals[0] + vals[1] == vals[2] else 'inconsistent'
    except (KeyError, InvalidOperation, TypeError):
        return 'missing'
