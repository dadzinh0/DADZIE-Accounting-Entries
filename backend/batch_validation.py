"""Conservative pre-classification checks; no accounting rule is yet approved."""
from decimal import Decimal, InvalidOperation
from extraction import validate_totals

def assess(fields, known_references=()):
    issues = []
    def issue(code, message):
        issues.append({'code': code, 'severity': 'critical', 'explanation': message})
    def value(key):
        item = fields.get(key) or {}
        return str(item.get('value') or '').strip()
    for key in ('supplier', 'invoice_number', 'invoice_date', 'currency', 'amount_ht', 'vat_amount', 'amount_ttc'):
        if not value(key): issue('missing_' + key, 'Champ obligatoire absent : ' + key)
    totals = validate_totals(fields)
    if totals != 'consistent': issue('totals_' + totals, 'Les montants ne sont pas vérifiés ou sont incohérents.')
    if value('currency') and value('currency').upper() != 'MAD':
        issue('unsupported_currency', 'Devise hors périmètre : revue nécessaire.')
    identity = (value('supplier').casefold(), value('invoice_number').casefold())
    if all(identity) and identity in known_references:
        issue('duplicate_reference', 'Référence fournisseur déjà présente : doublon possible.')
    # Never infer approval from arithmetic or extraction alone.
    issue('unverified_rule', 'Aucune règle comptable et fiscale validée ne couvre cette facture.')
    return {'status': 'review', 'issues': issues, 'eligible_for_export': False}
