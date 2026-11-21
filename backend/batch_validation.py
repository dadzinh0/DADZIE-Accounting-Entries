"""Conservative pre-classification checks; no accounting rule is yet approved."""
from decimal import Decimal, InvalidOperation
from extraction import validate_totals

def assess(fields, known_references=()):
    issues = []
    def issue(code, message, severity='critical', **details):
        issues.append({'code': code, 'severity': severity, 'explanation': message, **details})
    def value(key):
        item = fields.get(key) or {}
        return str(item.get('value') or '').strip()
    for key in ('supplier', 'invoice_number', 'invoice_date', 'currency', 'amount_ht', 'vat_amount', 'amount_ttc'):
        if not value(key): issue('missing_' + key, 'Champ obligatoire absent : ' + key)
    suggested = [key for key, field in fields.items() if isinstance(field, dict) and field.get('origin') == 'qwen_suggested']
    if suggested:
        issue('model_suggestion_review', 'Valeur(s) proposée(s) par Qwen : vérification humaine requise.',
              severity='warning', fields=suggested)
    calculated = [key for key, field in fields.items() if isinstance(field, dict) and field.get('origin') == 'calculated']
    if calculated:
        issue('calculated_total_review', 'Total(s) calculé(s) depuis un taux de TVA explicite : vérifier sur la facture.',
              severity='warning', fields=calculated)
    if (fields.get('supplier') or {}).get('origin') == 'ocr_uncertain':
        issue('uncertain_supplier', 'Nom du fournisseur lu dans le logo par OCR : vérifier l’orthographe.')
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
