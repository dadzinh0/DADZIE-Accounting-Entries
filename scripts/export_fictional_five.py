"""Generate a verified demonstration workbook from the five named fictional PDFs."""
import json
import os
import sys
from pathlib import Path
from sqlalchemy import select
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from main import Session, engine, Document, UPLOAD_DIR, extract_document
from batch_validation import assess
from extraction import validate_totals
from invoice_workbook import build_invoice_workbook

NAMES = [
    '01_achat_standard.pdf',
    '02_prestation_service.pdf',
    '03_plusieurs_lignes.pdf',
    '04_reference_manquante.pdf',
    '05_scan_total_incorrect.pdf',
]
items = []
with Session(engine) as session:
    for name in NAMES:
        doc = session.scalar(select(Document).where(Document.original_name == name).order_by(Document.created_at.desc()).limit(1))
        if doc is None:
            raise RuntimeError('Fictional fixture unavailable: ' + name)
        _, fields = extract_document((UPLOAD_DIR / doc.id).read_bytes())
        result = assess(fields)
        items.append({
            'name': name, 'document_id': doc.id, 'status': result['status'],
            'fields': fields, 'totals': validate_totals(fields), 'issues': result['issues'],
        })
out = Path(os.getenv('OUTPUT_PATH', '/tmp/proheat-fictional-invoice-details.xlsx'))
out.write_bytes(build_invoice_workbook(items))
print(json.dumps({'path': str(out), 'invoices': len(items), 'line_items': sum(len((x['fields'].get('lines') or {}).get('value') or []) for x in items), 'flagged': [x['name'] for x in items if x['totals'] != 'consistent' or not (x['fields'].get('invoice_number') or {}).get('value')]}, ensure_ascii=False))
