"""Optional local Ollama fallback for fields missed by deterministic extraction."""
import json
import os
import re
from urllib.error import URLError
from urllib.request import Request, urlopen


FIELD_NAMES = (
    'supplier', 'ice', 'invoice_number', 'invoice_date', 'due_date',
    'currency', 'amount_ht', 'vat_amount', 'amount_ttc',
)

SCHEMA = {
    'type': 'object',
    'properties': {
        name: {
            'type': 'object',
            'properties': {
                'value': {'type': ['string', 'null']},
                'evidence': {'type': ['string', 'null']},
            },
            'required': ['value', 'evidence'],
            'additionalProperties': False,
        }
        for name in FIELD_NAMES
    },
    'required': list(FIELD_NAMES),
    'additionalProperties': False,
}


def _normalize(text):
    return re.sub(r'\s+', ' ', str(text or '')).strip().casefold()


def enrich_missing_fields(fields, source_text):
    """Fill only missing fields when Ollama returns values with quoted evidence.

    Disabled unless OLLAMA_BASE_URL is configured. Failures are deliberately
    non-fatal so the normal deterministic/OCR flow remains available.
    """
    base_url = os.getenv('OLLAMA_BASE_URL', '').strip().rstrip('/')
    if not base_url or not source_text.strip():
        return fields

    missing = [name for name in FIELD_NAMES if not (fields.get(name) or {}).get('value')]
    if not missing:
        return fields

    model = os.getenv('OLLAMA_MODEL', 'qwen3-vl:4b').strip()
    prompt = (
        'Extract invoice fields from the supplied OCR/native PDF text. '
        'The document may be in French, Arabic, or another language. '
        'Use only explicit text evidence. Do not calculate or infer missing values. '
        'For each non-null value, include a short exact quote copied from the source. '
        'Return null for unavailable or ambiguous fields. Amounts must use a dot '
        'as decimal separator and no thousands separators. Dates use DD/MM/YYYY. '
        'Only these fields may be returned: ' + ', '.join(missing) + '.\n\n'
        'Already extracted values (do not change them): ' + json.dumps(
            {key: (fields.get(key) or {}).get('value') for key in FIELD_NAMES if key in fields},
            ensure_ascii=False,
        ) + '\n\nSOURCE TEXT:\n' + source_text[:50000]
    )
    body = json.dumps({
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'stream': False,
        'format': SCHEMA,
        'options': {'temperature': 0, 'num_ctx': 8192},
    }).encode('utf-8')
    request = Request(base_url + '/api/chat', data=body, headers={'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=float(os.getenv('OLLAMA_TIMEOUT_SECONDS', '120'))) as response:
            result = json.loads(response.read())
        suggestions = json.loads(result['message']['content'])
    except (URLError, TimeoutError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return fields

    normalized_source = _normalize(source_text)
    for name in missing:
        item = suggestions.get(name) or {}
        value = item.get('value')
        evidence = item.get('evidence')
        if not isinstance(value, str) or not value.strip() or not isinstance(evidence, str) or not evidence.strip():
            continue
        # Reject unsupported model guesses: its evidence must occur in the
        # extracted/OCR source. Keep the quote for user traceability.
        if _normalize(evidence) not in normalized_source:
            continue
        value = value.strip()
        evidence = evidence.strip()
        if name in ('amount_ht', 'vat_amount', 'amount_ttc'):
            value = value.replace('\u00a0', '').replace(' ', '').replace(',', '.')
            if not re.fullmatch(r'-?\d+(?:\.\d{1,4})?', value):
                continue
        fields[name] = {
            'value': value,
            'origin': 'qwen_suggested',
            'evidence': evidence,
        }
    return fields
