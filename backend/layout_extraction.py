"""Position-aware PDF extraction. Values remain tied to visible text or OCR."""
import re
from datetime import datetime

import pytesseract
from PIL import Image
import io
import fitz

from extraction import extract

MONEY = re.compile(r'\d[\d\s\u00a0]*[,.]\d{2}')
DATE = re.compile(r'\b(\d{2})[/-](\d{2})[/-](\d{2}|\d{4})\b')

def _put(fields, key, value, evidence, origin='extracted'):
    if value and key not in fields:
        fields[key] = {'value': value, 'origin': origin, 'evidence': evidence}

def _amount(text):
    match = MONEY.search(text)
    return match.group().replace(' ', '').replace('\u00a0', '').replace(',', '.') if match else None

def _rows(page):
    words = sorted(page.get_text('words'), key=lambda w: (round(w[1] / 3), w[0]))
    rows = []
    for word in words:
        if not rows or abs(rows[-1][0] - word[1]) > 3:
            rows.append((word[1], [word]))
        else:
            rows[-1][1].append(word)
    return [(y, sorted(items, key=lambda w: w[0])) for y, items in rows]

def _table_lines(page, rows):
    header = next(((y, words) for y, words in rows if any('Désignation' in w[4] for w in words)
                   and any('Qté' in w[4] for w in words) and any('Montant' in w[4] for w in words)), None)
    if not header: return []
    hy, hw = header
    x_desc = next(w[0] for w in hw if 'Désignation' in w[4])
    x_qty = next(w[0] for w in hw if 'Qté' in w[4])
    description_left = max(0, x_desc - .85 * (x_qty - x_desc))
    x_total = next(w[0] for w in hw if 'Montant' in w[4])
    x_unit = next((w[0] for w in hw if 'P.U.N.' in w[4]), None)
    if x_unit is None: x_unit = next((w[0] for w in hw if 'P.U.' in w[4]), None)
    if x_unit is None: return []
    data = [(y, words) for y, words in rows if hy + 8 < y < page.rect.height - 90]
    lines = []
    for pos, (y, words) in enumerate(data):
        if any(w[4].lower() in ('totaux', 'total') for w in words): break
        def column(left, right):
            return ' '.join(w[4] for w in words if left - 5 <= w[0] < right - 5)
        quantity = column(x_qty, x_unit)
        unit = column(x_unit, x_total)
        total = column(x_total, page.rect.width)
        q = _amount(quantity)
        u = _amount(unit)
        t = _amount(total)
        if not (q and u and t): continue
        description = ' '.join(w[4] for w in words if description_left <= w[0] < x_qty - 5)
        for yy, continuation in data[pos+1:]:
            if yy > y + 35 or any(w[0] >= x_total - 5 and MONEY.search(w[4]) for w in continuation): break
            extra = ' '.join(w[4] for w in continuation if description_left <= w[0] < x_qty - 5)
            if extra: description += ' ' + extra
        if description.strip():
            lines.append({'description': description.strip(), 'quantity': q, 'unit_price': u,
                          'amount_ht': t, 'origin': 'extracted'})
    return lines

def extract_pdf(pdf):
    text_parts = []
    for page in pdf:
        page_text = page.get_text()[:100000]
        if not page_text.strip():
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            if pix.width * pix.height > 20_000_000: raise ValueError('Page trop grande')
            page_text = pytesseract.image_to_string(Image.open(io.BytesIO(pix.tobytes('png'))), lang='fra', timeout=20)
        text_parts.append(page_text)
    text = '\n'.join(text_parts)
    fields = extract(text)
    ice_matches = re.findall(r'\bICE\s*:\s*([0-9]{15})\b', text, re.I)
    if len(set(ice_matches)) > 1:
        # The customer's ICE is often in the address block; the issuer's
        # registration appears with RC / IF / CNSS in the footer.
        issuer_ice = re.search(r'(?is)\bRC\s*N[°o]?\s*:.*?\bICE\s*:\s*([0-9]{15})', text)
        if issuer_ice:
            fields['ice'] = {'value': issuer_ice.group(1), 'origin': 'extracted', 'evidence': issuer_ice.group(0)[-75:]}
    number = re.search(r'(?i)\b(?:facture|invoice)\s*(?:n[°o]|num(?:é|e)ro|number|#)\s*:?\s*([A-Z0-9][A-Z0-9/-]{3,})', text)
    if number: _put(fields, 'invoice_number', number.group(1), number.group(0))
    if 'invoice_date' not in fields:
        for line in text.splitlines()[:40]:
            match = DATE.search(line)
            if match:
                day, month, year = match.groups()
                if len(year) == 2: year = '20' + year
                try: datetime(int(year), int(month), int(day))
                except ValueError: continue
                _put(fields, 'invoice_date', f'{day}/{month}/{year}', line)
                break
    if re.search(r'\b(?:Dhs|MAD|Dirhams?)\b', text, re.I):
        _put(fields, 'currency', 'MAD', 'Devise indiquée en Dhs/MAD')
    # The buyer often occupies the first selectable-text block. OCR the image
    # header independently, even on PDFs with an otherwise complete text layer.
    if 'supplier' not in fields and pdf.page_count:
        page = pdf[0]
        header = ''
        for image_info in page.get_images(full=True):
            image_data = pdf.extract_image(image_info[0])['image']
            image = Image.open(io.BytesIO(image_data))
            if image.width < 300 or image.height < 80 or image.width * image.height > 20_000_000: continue
            header += pytesseract.image_to_string(image, lang='fra', config='--psm 3', timeout=20) + '\n'
        if not header:
            clip = fitz.Rect(0, 0, page.rect.width, min(155, page.rect.height * .22))
            pix = page.get_pixmap(matrix=fitz.Matrix(4, 4), clip=clip, alpha=False)
            if pix.width * pix.height <= 20_000_000:
                header = pytesseract.image_to_string(Image.open(io.BytesIO(pix.tobytes('png'))), lang='fra', config='--psm 3', timeout=20)
        if header:
            for line in header.splitlines():
                candidate = line.strip(' |—-*')
                if re.search(r'(?i)\b(?:compagnie|société|societe|entreprise|company|sarl|s\.a\.)\b', candidate) and len(candidate) >= 12:
                    _put(fields, 'supplier', candidate, 'OCR du logo : ' + candidate, 'ocr_uncertain')
                    break
    # Read totals from aligned rows. This avoids confusing line-item prices
    # with invoice totals when PDF text order is column-major.
    for page in pdf:
        rows = _rows(page)
        table_lines = _table_lines(page, rows)
        if table_lines:
            existing = fields.get('lines', {}).get('value', [])
            fields['lines'] = {'value': existing + table_lines, 'origin': 'extracted', 'evidence': 'Colonnes de désignation, quantité, prix et montant'}
        for index, (y, words) in enumerate(rows):
            label = ' '.join(w[4] for w in words)
            for key, label_pattern in (('amount_ht', r'\btotal\s+HT\b'), ('vat_amount', r'\bTVA\s*\d*\s*%'), ('amount_ttc', r'\b(?:total\s+TTC|net\s+[àa]\s+payer)\b')):
                if key in fields or not re.search(label_pattern, label, re.I): continue
                candidates = []
                for yy, nearby in rows[max(0,index-1):min(len(rows),index+4)]:
                    if abs(yy-y) > 42: continue
                    for j, word in enumerate(nearby):
                        value = _amount(word[4])
                        previous_is_group = j > 0 and re.fullmatch(r'\d{1,3}', nearby[j-1][4]) and word[0] - nearby[j-1][2] < 8
                        if value and not previous_is_group: candidates.append((abs(yy-y), word[0], value))
                        elif re.fullmatch(r'\d{1,3}', word[4]) and j+1 < len(nearby) and re.fullmatch(r'\d{3}[,.]\d{2}', nearby[j+1][4]):
                            value = _amount(word[4] + ' ' + nearby[j+1][4])
                            if value: candidates.append((abs(yy-y), word[0], value))
                if candidates:
                    if key == 'amount_ttc':
                        _, _, value = max(candidates, key=lambda c: c[1])
                    else:
                        right_of_label = [c for c in candidates if c[1] > words[0][0] + 40]
                        _, _, value = min(right_of_label or candidates, key=lambda c: (c[1], c[0]))
                    _put(fields, key, value, label + ' / ' + value)
    return fields
