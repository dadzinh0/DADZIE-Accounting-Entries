import hashlib
import io
import os
import secrets
import uuid
import threading
import time
import shutil
from datetime import datetime, timezone
from pathlib import Path

import fitz
import pytesseract
from PIL import Image, UnidentifiedImageError
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Text, DateTime, ForeignKey, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from starlette.middleware.sessions import SessionMiddleware
from extraction import extract, validate_totals
from batch_validation import assess

DATABASE_URL = os.environ['DATABASE_URL']
SECRET = os.environ['SESSION_SECRET']
if len(SECRET) < 32 or 'replace-with' in SECRET:
    raise RuntimeError('SESSION_SECRET must be a random secret of at least 32 characters')
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', '/data/uploads'))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_BYTES = 10 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 20_000_000
hasher = PasswordHasher()

class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
class Document(Base):
    __tablename__ = 'documents'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    media_type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default='review')
    fields_json: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
class Audit(Base):
    __tablename__ = 'audit_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(100), default='')
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Batch(Base):
    __tablename__ = 'batches'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class BatchItem(Base):
    __tablename__ = 'batch_items'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey('batches.id'), index=True)
    name: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20), default='queued', index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey('documents.id'), nullable=True)
    issues_json: Mapped[str] = mapped_column(Text, default='[]')

import json
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=SECRET, same_site='strict', https_only=False, max_age=8*3600, session_cookie='proheat_session')

@app.on_event('startup')
def startup():
    Base.metadata.create_all(engine)
    # One worker per deployment. Processing is serialized and queued state survives restarts.
    threading.Thread(target=batch_worker, daemon=True, name='batch-worker').start()

def db():
    with Session(engine) as session:
        yield session

def user(request: Request, session: Session = Depends(db)):
    uid = request.session.get('uid')
    account = session.get(User, uid) if uid else None
    if not account: raise HTTPException(401, 'Connexion requise')
    return account

def audit(session, actor, action, entity=''):
    session.add(Audit(actor=actor, action=action, entity=entity))

class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r'^[A-Za-z0-9_.-]+$')
    password: str = Field(min_length=1, max_length=128)

class SetupCredentials(Credentials):
    password: str = Field(min_length=8, max_length=128)

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

@app.post('/api/change-password')
def change_password(data: PasswordChange, account: User = Depends(user), session: Session = Depends(db)):
    try:
        hasher.verify(account.password_hash, data.current_password)
    except VerificationError:
        raise HTTPException(400, 'Mot de passe actuel incorrect')
    if data.current_password == data.new_password:
        raise HTTPException(400, 'Choisissez un nouveau mot de passe différent')
    account.password_hash = hasher.hash(data.new_password)
    audit(session, account.username, 'changement_mot_de_passe')
    session.commit()
    return {'ok': True}

@app.get('/api/setup-status')
def setup_status(session: Session = Depends(db)):
    return {'needed': session.scalar(select(func.count()).select_from(User)) == 0}

@app.post('/api/setup')
def setup(data: SetupCredentials, session: Session = Depends(db)):
    # The DB uniqueness constraint guards duplicate usernames; setup is intended for
    # an isolated first run and must not be exposed to untrusted local users.
    if session.scalar(select(func.count()).select_from(User)): raise HTTPException(403, 'Configuration déjà effectuée')
    session.add(User(username=data.username, password_hash=hasher.hash(data.password), role='admin'))
    audit(session, data.username, 'initialisation_administrateur')
    session.commit()
    return {'ok': True}

@app.post('/api/login')
def login(data: Credentials, request: Request, session: Session = Depends(db)):
    account = session.scalar(select(User).where(User.username == data.username))
    try:
        if not account or not hasher.verify(account.password_hash, data.password): raise ValueError()
    except (VerificationError, ValueError):
        raise HTTPException(401, 'Identifiants incorrects')
    request.session.clear(); request.session['uid'] = account.id
    audit(session, account.username, 'connexion'); session.commit()
    return {'username': account.username, 'role': account.role}

@app.post('/api/logout')
def logout(request: Request, account: User = Depends(user), session: Session = Depends(db)):
    audit(session, account.username, 'deconnexion'); session.commit(); request.session.clear()
    return {'ok': True}

@app.get('/api/me')
def me(account: User = Depends(user)): return {'username': account.username, 'role': account.role}

def document_dict(doc):
    fields = json.loads(doc.fields_json)
    return {'id': doc.id, 'name': doc.original_name, 'status': doc.status, 'fields': fields, 'totals': validate_totals(fields), 'created_at': doc.created_at.isoformat()}

def extract_document(data):
    text = ''
    if data.startswith(b'%PDF-'):
        media = 'application/pdf'
        with fitz.open(stream=data, filetype='pdf') as pdf:
            if pdf.page_count > 20: raise ValueError('Trop de pages')
            for page in pdf:
                page_text = page.get_text()[:100000]
                if not page_text.strip():
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                    if pix.width * pix.height > 20_000_000: raise ValueError('Page trop grande')
                    page_text = pytesseract.image_to_string(Image.open(io.BytesIO(pix.tobytes('png'))), lang='fra', timeout=20)
                text += page_text + '\n'
    else:
        image = Image.open(io.BytesIO(data))
        if image.format not in ('JPEG', 'PNG'): raise ValueError('Format non pris en charge')
        media = 'image/jpeg' if image.format == 'JPEG' else 'image/png'
        image.verify()
        image = Image.open(io.BytesIO(data))
        text = pytesseract.image_to_string(image, lang='fra', timeout=20)
    return media, extract(text)

def process_batch_item(item_id):
    with Session(engine) as session:
        item = session.get(BatchItem, item_id)
        if not item or item.status != 'queued': return
        try:
            existing = session.scalar(select(Document).where(Document.sha256 == item.sha256, Document.id != item.id).order_by(Document.created_at, Document.id).limit(1))
            data = (UPLOAD_DIR / item.id).read_bytes()
            media, fields = extract_document(data)
            references = set()
            for doc in session.scalars(select(Document).where(Document.id != item.id)).all():
                old = json.loads(doc.fields_json)
                supplier = str((old.get('supplier') or {}).get('value') or '').strip().casefold()
                number = str((old.get('invoice_number') or {}).get('value') or '').strip().casefold()
                if supplier and number: references.add((supplier, number))
            result = assess(fields, references)
            if existing:
                origin = session.scalar(select(BatchItem).where(BatchItem.id == existing.id).limit(1))
                scope = 'same_batch' if origin and origin.batch_id == item.batch_id else 'earlier_upload'
                label = 'même lot' if scope == 'same_batch' else 'import précédent'
                detail = f'Doublon exact ({label}) : document {existing.id}'
                if origin: detail += f', lot {origin.batch_id}'
                result['issues'].insert(0, {'code':'duplicate_file', 'severity':'critical', 'explanation':detail, 'duplicate_scope':scope, 'original_document_id':existing.id, 'original_batch_id':origin.batch_id if origin else None})
            doc = session.get(Document, item.id)
            if doc is None:
                doc = Document(id=item.id, original_name=item.name, sha256=item.sha256, media_type=media, fields_json=json.dumps(fields, ensure_ascii=False))
                session.add(doc); session.flush()
            else:
                # A retry of the same item is not a new invoice or its own duplicate.
                doc.media_type = media; doc.fields_json = json.dumps(fields, ensure_ascii=False)
            item.document_id = doc.id; item.status = result['status']
            item.issues_json = json.dumps(result['issues'], ensure_ascii=False)
            audit(session, session.get(Batch, item.batch_id).actor, 'traitement_lot', item.id)
            session.commit()
        except Exception:
            session.rollback()
            item = session.get(BatchItem, item_id)
            item.status = 'failed'
            item.issues_json = json.dumps([{'code':'processing_failed','severity':'critical','explanation':'Document illisible ou traitement impossible.'}], ensure_ascii=False)
            session.commit()

def batch_worker():
    while True:
        try:
            with Session(engine) as session:
                item_id = session.scalar(select(BatchItem.id).where(BatchItem.status == 'queued').order_by(BatchItem.id).limit(1))
            if item_id: process_batch_item(item_id)
            else: time.sleep(2)
        except Exception:
            time.sleep(5)

@app.post('/api/batches')
async def create_batch(files: list[UploadFile] = File(...), account: User = Depends(user), session: Session = Depends(db)):
    if not 1 <= len(files) <= 100: raise HTTPException(400, 'Choisissez entre 1 et 100 fichiers.')
    batch = Batch(id=str(uuid.uuid4()), actor=account.username)
    session.add(batch)
    paths = []
    try:
        for upload_file in files:
            data = await upload_file.read(MAX_BYTES + 1)
            if not data or len(data) > MAX_BYTES: raise HTTPException(400, 'Fichier vide ou supérieur à 10 Mo.')
            item_id = str(uuid.uuid4())
            path = UPLOAD_DIR / item_id
            path.write_bytes(data); paths.append(path)
            session.add(BatchItem(id=item_id, batch_id=batch.id, name=Path(upload_file.filename or 'document').name[:255], sha256=hashlib.sha256(data).hexdigest()))
        audit(session, account.username, 'creation_lot', batch.id)
        session.commit()
    except Exception:
        session.rollback()
        for path in paths: path.unlink(missing_ok=True)
        raise
    return {'id': batch.id}

@app.get('/api/batches')
def list_batches(account: User = Depends(user), session: Session = Depends(db)):
    return [{'id': b.id, 'created_at': b.created_at.isoformat()} for b in session.scalars(select(Batch).order_by(Batch.created_at.desc()).limit(100))]

@app.post('/api/batches/{batch_id}/reprocess')
def reprocess_batch(batch_id: str, account: User = Depends(user), session: Session = Depends(db)):
    if not session.get(Batch, batch_id): raise HTTPException(404)
    originals = session.scalars(select(BatchItem).where(BatchItem.batch_id == batch_id)).all()
    if not originals or any(x.status == 'queued' for x in originals):
        raise HTTPException(409, 'Attendez la fin du lot avant de le retraiter.')
    batch = Batch(id=str(uuid.uuid4()), actor=account.username)
    session.add(batch); paths = []
    try:
        for original in originals:
            item_id = str(uuid.uuid4()); path = UPLOAD_DIR / item_id
            shutil.copyfile(UPLOAD_DIR / original.id, path); paths.append(path)
            session.add(BatchItem(id=item_id, batch_id=batch.id, name=original.name, sha256=original.sha256))
        audit(session, account.username, 'retraitement_lot', batch_id + ':' + batch.id)
        session.commit()
    except Exception:
        session.rollback()
        for path in paths: path.unlink(missing_ok=True)
        raise
    return {'id': batch.id}

@app.get('/api/batches/{batch_id}')
def get_batch(batch_id: str, account: User = Depends(user), session: Session = Depends(db)):
    batch = session.get(Batch, batch_id)
    if not batch: raise HTTPException(404)
    items = session.scalars(select(BatchItem).where(BatchItem.batch_id == batch_id).order_by(BatchItem.id)).all()
    result = []
    for item in items:
        doc = session.get(Document, item.document_id) if item.document_id else None
        fields = json.loads(doc.fields_json) if doc else {}
        result.append({'id':item.id, 'name':item.name, 'status':item.status, 'document_id':item.document_id, 'supplier':fields.get('supplier', {}).get('value'), 'invoice_number':fields.get('invoice_number', {}).get('value'), 'amount_ht':fields.get('amount_ht', {}).get('value'), 'vat_amount':fields.get('vat_amount', {}).get('value'), 'amount_ttc':fields.get('amount_ttc', {}).get('value'), 'fields':fields, 'totals':validate_totals(fields), 'issues':json.loads(item.issues_json)})
    attention = lambda x: any(issue.get('code') not in ('unverified_rule', 'duplicate_file') for issue in x['issues'])
    return {'id':batch.id, 'items':result, 'total':len(items), 'processed':sum(i.status != 'queued' for i in items), 'review':sum(i.status == 'review' for i in items), 'failed':sum(i.status == 'failed' for i in items), 'validated':0, 'attention':sum(attention(i) for i in result), 'extracted':sum(i['status'] == 'review' and not attention(i) for i in result)}

@app.get('/api/batches/{batch_id}/exceptions.xlsx')
def batch_exceptions(batch_id: str, account: User = Depends(user), session: Session = Depends(db)):
    from batch_report import build_exception_report
    result = get_batch(batch_id, account, session)
    if result['processed'] != result['total']: raise HTTPException(409, 'Le lot est encore en cours de traitement.')
    content = build_exception_report(result['items'])
    audit(session, account.username, 'export_anomalies', batch_id); session.commit()
    return Response(content, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition':'attachment; filename="anomalies.xlsx"', 'X-Content-Type-Options':'nosniff'})

@app.get('/api/batches/{batch_id}/invoice-data.xlsx')
def batch_invoice_data(batch_id: str, account: User = Depends(user), session: Session = Depends(db)):
    from invoice_workbook import build_invoice_workbook
    result = get_batch(batch_id, account, session)
    if result['processed'] != result['total']: raise HTTPException(409, 'Le lot est encore en cours de traitement.')
    # Earlier batches may point duplicates at an older document whose fields were
    # empty. Re-extract from this batch item's own preserved file for the report.
    for item in result['items']:
        try:
            _, fields = extract_document((UPLOAD_DIR / item['id']).read_bytes())
            item['fields'] = fields
            item['totals'] = validate_totals(fields)
            item['issues'] = assess(fields)['issues'] + [issue for issue in item['issues'] if issue.get('code') == 'duplicate_file']
        except Exception:
            item['issues'].append({'code':'report_extraction_failed','severity':'critical','explanation':'Extraction impossible lors de la création du fichier Excel.'})
    content = build_invoice_workbook(result['items'])
    audit(session, account.username, 'export_donnees_factures', batch_id); session.commit()
    return Response(content, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition':'attachment; filename="donnees_factures.xlsx"', 'X-Content-Type-Options':'nosniff'})

@app.get('/api/documents')
def documents(account: User = Depends(user), session: Session = Depends(db)):
    return [document_dict(d) for d in session.scalars(select(Document).where(Document.status != 'deleted').order_by(Document.created_at.desc())).all()]

@app.delete('/api/documents/{doc_id}')
def delete_document(doc_id: str, account: User = Depends(user), session: Session = Depends(db)):
    if account.role != 'admin': raise HTTPException(403, 'Action réservée à l’administrateur')
    doc = session.get(Document, doc_id)
    if not doc or doc.status == 'deleted': raise HTTPException(404)
    doc.status = 'deleted'
    audit(session, account.username, 'suppression_document', doc_id)
    session.commit()
    return {'ok': True}

@app.post('/api/documents')
async def upload(file: UploadFile = File(...), account: User = Depends(user), session: Session = Depends(db)):
    data = await file.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES: raise HTTPException(400, 'Fichier vide ou supérieur à 10 Mo')
    digest = hashlib.sha256(data).hexdigest()
    duplicate = session.scalar(select(Document).where(Document.sha256 == digest))
    if duplicate: raise HTTPException(409, 'Fichier identique déjà importé : ' + duplicate.id)
    text = ''
    try:
        if data.startswith(b'%PDF-'):
            media = 'application/pdf'
            with fitz.open(stream=data, filetype='pdf') as pdf:
                if pdf.page_count > 20: raise ValueError('Trop de pages')
                for page in pdf:
                    page_text = page.get_text()[:100000]
                    if not page_text.strip():
                        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                        if pix.width * pix.height > 20_000_000: raise ValueError('Page trop grande')
                        page_text = pytesseract.image_to_string(Image.open(io.BytesIO(pix.tobytes('png'))), lang='fra', timeout=20)
                    text += page_text + '\n'
        else:
            image = Image.open(io.BytesIO(data))
            if image.format not in ('JPEG', 'PNG'): raise ValueError('Format non pris en charge')
            media = 'image/jpeg' if image.format == 'JPEG' else 'image/png'
            image.verify()
            image = Image.open(io.BytesIO(data))
            text = pytesseract.image_to_string(image, lang='fra', timeout=20)
    except (ValueError, RuntimeError, UnidentifiedImageError, OSError, fitz.FileDataError):
        raise HTTPException(400, 'Document illisible, trop volumineux ou traitement impossible')
    doc_id = str(uuid.uuid4())
    path = UPLOAD_DIR / doc_id
    path.write_bytes(data)
    try:
        doc = Document(id=doc_id, original_name=Path(file.filename or 'document').name[:255], sha256=digest, media_type=media, fields_json=json.dumps(extract(text), ensure_ascii=False))
        session.add(doc); audit(session, account.username, 'import_document', doc_id); session.commit()
    except Exception:
        path.unlink(missing_ok=True); raise
    return document_dict(doc)

@app.get('/api/documents/{doc_id}/file')
def get_file(doc_id: str, account: User = Depends(user), session: Session = Depends(db)):
    doc = session.get(Document, doc_id)
    if not doc: raise HTTPException(404)
    return FileResponse(UPLOAD_DIR / doc.id, media_type=doc.media_type, headers={'Content-Disposition': 'inline', 'X-Content-Type-Options': 'nosniff'})

class Review(BaseModel):
    fields: dict[str, str | None]
    decision: str = Field(pattern='^(save|reject)$')

@app.put('/api/documents/{doc_id}')
def review(doc_id: str, data: Review, account: User = Depends(user), session: Session = Depends(db)):
    doc = session.get(Document, doc_id)
    if not doc: raise HTTPException(404)
    permitted = {'supplier', 'invoice_number', 'invoice_date', 'ice', 'currency', 'amount_ht', 'vat_amount', 'amount_ttc'}
    if set(data.fields) - permitted: raise HTTPException(400, 'Champ inconnu')
    fields = json.loads(doc.fields_json)
    for key, value in data.fields.items():
        if value is not None and len(value) > 255: raise HTTPException(400, 'Valeur trop longue')
        if value != fields.get(key, {}).get('value'):
            fields[key] = {'value': value, 'origin': 'manual'}
    doc.fields_json = json.dumps(fields, ensure_ascii=False)
    doc.status = 'rejected' if data.decision == 'reject' else 'review'
    audit(session, account.username, 'rejet_document' if data.decision == 'reject' else 'modification_document', doc.id)
    session.commit(); return document_dict(doc)

@app.get('/api/audit')
def audit_log(account: User = Depends(user), session: Session = Depends(db)):
    if account.role != 'admin': raise HTTPException(403)
    return [{'actor': x.actor, 'action': x.action, 'entity': x.entity, 'at': x.at.isoformat()} for x in session.scalars(select(Audit).order_by(Audit.id.desc()).limit(200))]

FRONTEND_DIR = os.getenv('FRONTEND_DIR', '/app/frontend')

@app.get('/app.js')
def frontend_script():
    return FileResponse(Path(FRONTEND_DIR) / 'app.js', media_type='application/javascript', headers={'Cache-Control':'no-store'})

@app.get('/')
def frontend_index():
    return FileResponse(Path(FRONTEND_DIR) / 'index.html', media_type='text/html', headers={'Cache-Control':'no-store'})

app.mount('/', StaticFiles(directory=FRONTEND_DIR, html=True), name='frontend')
