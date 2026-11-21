"""Create an entirely fictional PDF invoice without any external dependency."""
from pathlib import Path

lines = [
    'DOCUMENT FICTIF - SANS VALEUR COMPTABLE',
    'Fournisseur: Atelier Exemple Fictif',
    'Facture No: TEST-2026-001',
    'Date: 01/11/2026',
    'Devise: MAD',
    'HT: 1000,00',
    'TVA: 200,00',
    'TTC: 1200,00',
]
stream = 'BT /F1 14 Tf 50 770 Td 20 TL ' + ' '.join(f'({line}) Tj T*' for line in lines) + ' ET'
objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    f'<< /Length {len(stream.encode("ascii"))} >>\nstream\n{stream}\nendstream',
]
data = bytearray(b'%PDF-1.4\n')
offsets = [0]
for i, obj in enumerate(objects, 1):
    offsets.append(len(data)); data.extend(f'{i} 0 obj\n{obj}\nendobj\n'.encode('ascii'))
xref = len(data)
data.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode('ascii'))
for offset in offsets[1:]: data.extend(f'{offset:010} 00000 n \n'.encode('ascii'))
data.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode('ascii'))
target = Path(__file__).parent / 'fixtures' / 'facture-fictive.pdf'
target.parent.mkdir(exist_ok=True)
target.write_bytes(data)
print(target)
